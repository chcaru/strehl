//! Bounded nomination diversity. A large focus plateau must not spend every
//! original-image slot on neighboring acquisitions of the same spatial patch.
//! These scores nominate image measurements; they never certify geometry/depth.
use super::*;
use std::collections::BTreeMap;

#[derive(Clone, Debug, Serialize)]
pub struct Nomination {
    pub source: usize,
    pub marginal_weighted_support: u64,
    pub total_weighted_support: u64,
    pub occupied_bins: usize,
    pub spatial_bin_side: usize,
    pub minimum_acquisition_separation: usize,
    pub newly_covered_qualified_focus_pixels: u64,
}

#[derive(Clone, Debug, Serialize)]
pub struct Coverage {
    pub maximum_streamed_sources: usize,
    pub width_implied_requested_sources: usize,
    pub selected_sources: usize,
    pub qualified_focus_pixels: u64,
    pub qualified_focus_covered_pixels: u64,
    pub focus_width_p10_frames: Option<f32>,
    pub remaining_focus_intervals: Vec<(usize, usize, u64)>,
    pub policy: &'static str,
}

pub(super) fn select(
    guide: &MosaicGuide,
    range: std::ops::Range<usize>,
    maximum: usize,
) -> Result<(Vec<Nomination>, Coverage)> {
    guide.validate()?;
    ensure!(
        !range.is_empty() && maximum > 0,
        "empty original nomination range/budget"
    );
    // About32 cells across the guide; smaller edge cells carry proportionally
    // less observed area. Integer rank weights preserve deterministic ties.
    let side = guide
        .geometry
        .width
        .max(guide.geometry.height)
        .div_ceil(32)
        .max(8);
    let columns = guide.geometry.width.div_ceil(side);
    let bins = columns
        .checked_mul(guide.geometry.height.div_ceil(side))
        .context("source coverage grid overflow")?;
    let mut support = BTreeMap::<usize, BTreeMap<usize, u32>>::new();
    for (pixel, (ids, &covered)) in guide.source_indices.iter().zip(&guide.covered).enumerate() {
        if !covered {
            continue;
        }
        let bin =
            (pixel / guide.geometry.width / side) * columns + pixel % guide.geometry.width / side;
        for (rank, &source) in ids.iter().enumerate() {
            if source == usize::MAX {
                continue;
            }
            ensure!(
                range.contains(&source),
                "mosaic feature witness outside its declared pass"
            );
            let count = support.entry(source).or_default().entry(bin).or_default();
            *count = count
                .checked_add((4 - rank) as u32)
                .context("source coverage count overflow")?;
        }
    }
    // Qualified focus bands are actual observed acquisition intervals. Cover
    // these before spending more slots on ambiguous high-area plateaus. Never
    // impose a frame-count spacing that skips a known narrow band.
    let mut intervals = BTreeMap::<(usize, usize), u64>::new();
    let mut widths = Vec::new();
    for i in 0..guide.geometry.pixels() {
        if !guide.covered[i] || !guide.usable_focus[i] {
            continue;
        }
        let ordinal = guide.focus_ordinal[i];
        let width = guide.focus_width[i];
        if !ordinal.is_finite() || !width.is_finite() || width < 0.0 {
            continue;
        }
        let lo = (ordinal - width).ceil().max(0.0) as usize;
        let hi = (ordinal + width).floor().max(0.0) as usize;
        if lo >= range.len() || lo > hi {
            continue;
        }
        widths.push(width);
        *intervals
            .entry((lo + range.start, hi.min(range.len() - 1) + range.start))
            .or_default() += 1;
    }
    widths.sort_by(f32::total_cmp);
    let width_p10 = (!widths.is_empty()).then(|| widths[widths.len() / 10]);
    let requested = width_p10
        .map_or(maximum, |w| {
            (range.len() as f64 / (2.0 * f64::from(w)).max(1.0)).ceil() as usize
        })
        .max(16)
        .min(range.len());
    let qualified = intervals.values().sum::<u64>();
    let mut focus_votes = vec![0_u64; range.len()];
    for (&(lo, hi), &count) in &intervals {
        for vote in &mut focus_votes[lo - range.start..=hi - range.start] {
            *vote += count;
        }
    }
    let mut covered = vec![0_u32; bins];
    let mut chosen: Vec<Nomination> = Vec::new();
    while chosen.len() < maximum {
        let mut best = None;
        for (&source, counts) in &support {
            if chosen.iter().any(|n| source == n.source) {
                continue;
            }
            let gain: u64 = counts
                .iter()
                .map(|(&bin, &count)| u64::from(count.saturating_sub(covered[bin])))
                .sum();
            let focus_gain = focus_votes[source - range.start];
            if (gain > 0 || focus_gain > 0)
                && best.is_none_or(|(_, f, g)| (focus_gain, gain) > (f, g))
            {
                best = Some((source, focus_gain, gain));
            }
        }
        let Some((source, focus_gain, gain)) = best else {
            break;
        };
        let counts = &support[&source];
        chosen.push(Nomination {
            source,
            marginal_weighted_support: gain,
            total_weighted_support: counts.values().map(|&n| u64::from(n)).sum(),
            occupied_bins: counts.len(),
            spatial_bin_side: side,
            minimum_acquisition_separation: 1,
            newly_covered_qualified_focus_pixels: focus_gain,
        });
        for (&bin, &count) in counts {
            covered[bin] = covered[bin].max(count);
        }
        let hit: Vec<_> = intervals
            .keys()
            .copied()
            .filter(|&(lo, hi)| (lo..=hi).contains(&source))
            .collect();
        for interval in hit {
            let count = intervals.remove(&interval).expect("known focus interval");
            for vote in &mut focus_votes[interval.0 - range.start..=interval.1 - range.start] {
                *vote -= count;
            }
        }
    }
    let coverage = Coverage {
        maximum_streamed_sources: maximum,
        width_implied_requested_sources: requested,
        selected_sources: chosen.len(),
        qualified_focus_pixels: qualified,
        qualified_focus_covered_pixels: qualified - intervals.values().sum::<u64>(),
        focus_width_p10_frames: width_p10,
        remaining_focus_intervals: intervals
            .into_iter()
            .map(|((lo, hi), count)| (lo, hi, count))
            .collect(),
        policy: "Qualified focus-interval coverage first, then marginal spatial witness support. One-original streaming; no frame-count spacing; remaining intervals retain absolute census IDs. Nominations only, never depth/quality certificates.",
    };
    Ok((chosen, coverage))
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn diverse_source_nomination_retains_region_lost_to_neighbor_plateau() {
        let mut guide = super::super::super::tests::guide(0, 714, [0, 0], false);
        guide.covered.fill(false);
        guide.source_indices.fill([usize::MAX; 4]);
        let w = guide.geometry.width;
        // Sixteen adjacent originals partition one region into tiny interleaved
        // patches. Their descriptions see nearly the same image. A smaller,
        // separate region belongs to an acquisition far from that plateau.
        for y in 32..160 {
            for x in 32..288 {
                let p = y * w + x;
                guide.covered[p] = true;
                guide.source_indices[p][0] = 40 + (x + y) % 16;
            }
        }
        for y in 192..200 {
            for x in 320..328 {
                let p = y * w + x;
                guide.covered[p] = true;
                guide.source_indices[p][0] = 100;
            }
        }
        guide.usable_focus.fill(false);
        let mut totals = BTreeMap::<usize, usize>::new();
        for (ids, &valid) in guide.source_indices.iter().zip(&guide.covered) {
            if valid {
                *totals.entry(ids[0]).or_default() += 4;
            }
        }
        let mut old: Vec<_> = totals.into_iter().collect();
        old.sort_by(|a, b| b.1.cmp(&a.1).then(a.0.cmp(&b.0)));
        old.truncate(16);
        assert!(
            !old.iter().any(|&(id, _)| id == 100),
            "the causal old-ranking foil must lose the small region"
        );
        let (selected, _) = select(&guide, 0..128, 16).unwrap();
        assert!(selected.iter().any(|n| n.source == 100));
        assert!(selected.len() <= 16);
        assert!(selected.iter().all(|n| n.marginal_weighted_support > 0));
        for (i, a) in selected.iter().enumerate() {
            for b in &selected[i + 1..] {
                assert_ne!(a.source, b.source);
            }
        }
        let (again, _) = select(&guide, 0..128, 16).unwrap();
        assert_eq!(
            selected.iter().map(|n| n.source).collect::<Vec<_>>(),
            again.iter().map(|n| n.source).collect::<Vec<_>>()
        );
    }

    #[test]
    fn qualified_narrow_focus_bands_are_not_skipped_by_nomination_spacing() {
        let mut guide = super::super::super::tests::guide(0, 714, [0, 0], false);
        guide.covered.fill(false);
        guide.usable_focus.fill(false);
        guide.source_indices.fill([usize::MAX; 4]);
        for source in 0..64 {
            let i = 1000 + source * 4;
            guide.covered[i] = true;
            guide.usable_focus[i] = true;
            guide.focus_ordinal[i] = source as f32;
            guide.focus_width[i] = 0.25;
            guide.source_indices[i][0] = source;
        }
        let (_, limited) = select(&guide, 0..64, 16).unwrap();
        assert_eq!(limited.qualified_focus_covered_pixels, 16);
        assert_eq!(limited.remaining_focus_intervals.len(), 48);
        let (selected, complete) = select(&guide, 0..64, 128).unwrap();
        assert_eq!(selected.len(), 64);
        assert_eq!(complete.width_implied_requested_sources, 64);
        assert_eq!(complete.qualified_focus_covered_pixels, 64);
        assert!(complete.remaining_focus_intervals.is_empty());
    }
}
