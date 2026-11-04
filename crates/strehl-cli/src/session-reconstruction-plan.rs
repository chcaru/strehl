//! Compact full-sweep focus maps and bounded original-source tile scheduling.
//! These rasters contain decisions, never aligned source image samples.
use crate::session_sampling::SamplingDomain;
use anyhow::{Context, Result, ensure};
use std::collections::BTreeSet;
use std::ops::Range;
use strehl_core::focus_evidence::FocusEvidence;
use strehl_core::reconstruction::{MAX_SOURCES, focus_mode_response};

pub(super) struct FocusSummary {
    pub domain: SamplingDomain,
    pub frames: Range<usize>,
    pub ordinal: Vec<f32>,
    pub width: Vec<f32>,
    pub qualified: Vec<bool>,
}
impl FocusSummary {
    pub fn from_evidence(
        field: &FocusEvidence,
        frames: Range<usize>,
        domain: SamplingDomain,
    ) -> Result<Self> {
        domain.validate()?;
        ensure!(
            field.geometry.width == domain.width && field.geometry.height == domain.height,
            "reconstruction focus field differs from the sampling domain"
        );
        ensure!(
            field.frames.len() == frames.len()
                && field
                    .frames
                    .iter()
                    .enumerate()
                    .all(|(i, f)| f.global_index == frames.start + i),
            "reconstruction focus field lost original acquisition ordinals"
        );
        Ok(Self {
            domain,
            frames,
            ordinal: field.ordinal.clone(),
            width: field.width_frames.clone(),
            qualified: field
                .usable
                .iter()
                .zip(&field.flags)
                .map(|(&usable, &flags)| usable && flags == 0)
                .collect(),
        })
    }
    pub fn response(&self, source: usize, quad: usize) -> f32 {
        if !self.frames.contains(&source) {
            return 0.;
        }
        focus_mode_response(
            (source - self.frames.start) as f32,
            self.ordinal[quad],
            self.width[quad],
            self.qualified[quad],
        )
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) struct Rect {
    pub x: usize,
    pub y: usize,
    pub width: usize,
    pub height: usize,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) enum Skip {
    NoFocus,
    SourceBudget,
    NoIndependentGuide,
}
#[derive(Debug)]
pub(super) struct Tile {
    pub rect: Rect,
    pub sources: Vec<usize>,
    pub guides: Vec<usize>,
    pub skip: Option<Skip>,
}

pub(super) fn summary_bytes(domain: SamplingDomain, passes: usize) -> Result<usize> {
    domain
        .pixels()
        .checked_mul(9)
        .and_then(|v| v.checked_mul(passes))
        .and_then(|v| v.checked_add(passes.checked_mul(256)?))
        .context("reconstruction focus map reservation overflow")
}

/// Conservative Vec capacity and largest transient nomination-set allowance.
/// The final tile reports are streamed and never retained with this plan.
pub(super) fn plan_bytes(domain: SamplingDomain, passes: usize, frames: usize) -> Result<usize> {
    domain.validate()?;
    // An even split of a34-pixel remainder produces16+18, although splitting
    // stops at32. Reserve16-pixel cells, separately from Vec capacity below.
    let leaves = (domain.width * 2)
        .div_ceil(16)
        .checked_mul((domain.height * 2).div_ceil(16))
        .context("reconstruction tile count overflow")?;
    let per_tile = passes
        .checked_mul(2)
        .and_then(|v| v.checked_add(MAX_SOURCES))
        .and_then(|v| v.checked_mul(std::mem::size_of::<usize>() * 2))
        .and_then(|v| {
            v.checked_add(std::mem::size_of::<Tile>() * 2 + std::mem::size_of::<Rect>() * 2)
        })
        .context("reconstruction tile plan overflow")?;
    leaves
        .checked_mul(per_tile)
        .and_then(|v| v.checked_add(frames.checked_mul(128)?))
        .context("reconstruction tile plan reservation overflow")
}

fn nominate(
    rect: Rect,
    domain: SamplingDomain,
    maps: &[FocusSummary],
    placed: &[bool],
) -> Result<Tile> {
    let mut sources = BTreeSet::new();
    for map in maps {
        for y in rect.y / 2..(rect.y + rect.height).div_ceil(2) {
            for x in rect.x / 2..(rect.x + rect.width).div_ceil(2) {
                let q = y * domain.width + x;
                if !map.qualified[q] {
                    continue;
                }
                let (mode, width) = (map.ordinal[q], map.width[q]);
                if !mode.is_finite() || !width.is_finite() || width <= 0. {
                    continue;
                }
                let lo = (mode - width).ceil().max(0.) as usize;
                let hi = ((mode + width).floor().max(0.) as usize)
                    .min(map.frames.len().saturating_sub(1));
                for ordinal in lo..=hi {
                    let source = map.frames.start + ordinal;
                    if source < map.frames.end && placed[source] && map.response(source, q) > 0. {
                        sources.insert(source);
                    }
                }
            }
        }
    }
    let mut guides = BTreeSet::new();
    for map in maps {
        let selected: Vec<_> = sources.range(map.frames.clone()).copied().collect();
        let (Some(&first), Some(&last)) = (selected.first(), selected.last()) else {
            continue;
        };
        // Reserve photons before any candidate evaluation: nearest available
        // acquisition outside this tile's entire target union on either side.
        if let Some(i) = (map.frames.start..first).rev().find(|&i| placed[i]) {
            guides.insert(i);
        }
        if let Some(i) = (last + 1..map.frames.end).find(|&i| placed[i]) {
            guides.insert(i);
        }
    }
    ensure!(
        sources.is_disjoint(&guides),
        "a guide acquisition was also a reconstruction target"
    );
    let skip = if sources.is_empty() {
        Some(Skip::NoFocus)
    } else if guides.is_empty() {
        Some(Skip::NoIndependentGuide)
    } else {
        None
    };
    Ok(Tile {
        rect,
        sources: sources.into_iter().collect(),
        guides: guides.into_iter().collect(),
        skip,
    })
}

pub(super) fn tiles(
    domain: SamplingDomain,
    maps: &[FocusSummary],
    placed: &[bool],
    pin_limit: usize,
) -> Result<Vec<Tile>> {
    domain.validate()?;
    ensure!(
        pin_limit > 0,
        "no original-CFA handle fits the reconstruction budget"
    );
    ensure!(
        maps.iter().all(|m| m.domain == domain
            && m.frames.start < m.frames.end
            && m.frames.end <= placed.len()
            && m.ordinal.len() == domain.pixels()
            && m.width.len() == domain.pixels()
            && m.qualified.len() == domain.pixels()),
        "invalid compact reconstruction focus map"
    );
    let mut pending = Vec::new();
    for y in (0..domain.height * 2).step_by(64) {
        for x in (0..domain.width * 2).step_by(128) {
            pending.push(Rect {
                x,
                y,
                width: 128.min(domain.width * 2 - x),
                height: 64.min(domain.height * 2 - y),
            });
        }
    }
    pending.reverse();
    let mut output = Vec::new();
    while let Some(rect) = pending.pop() {
        let mut tile = nominate(rect, domain, maps, placed)?;
        if tile.sources.len() > MAX_SOURCES || tile.sources.len() + tile.guides.len() > pin_limit {
            // Subdivision preserves every eligible source. Never trim a
            // competing depth layer just to make a fixed-size source list fit.
            if rect.width >= rect.height && rect.width > 32 {
                let left = (rect.width / 4) * 2;
                pending.push(Rect {
                    x: rect.x + left,
                    width: rect.width - left,
                    ..rect
                });
                pending.push(Rect {
                    width: left,
                    ..rect
                });
                continue;
            } else if rect.height > 32 {
                let top = (rect.height / 4) * 2;
                pending.push(Rect {
                    y: rect.y + top,
                    height: rect.height - top,
                    ..rect
                });
                pending.push(Rect {
                    height: top,
                    ..rect
                });
                continue;
            }
            // Broad unresolved source sets can be much larger than64. Drop
            // their allocation too; retaining empty capacity defeats the plan.
            tile.sources = Vec::new();
            tile.guides = Vec::new();
            tile.skip = Some(Skip::SourceBudget);
        }
        output.push(tile);
    }
    Ok(output)
}

#[cfg(test)]
mod tests {
    use super::*;
    use strehl_core::plane::PlaneGeometry;
    fn domain(w: usize, h: usize) -> SamplingDomain {
        SamplingDomain {
            full: PlaneGeometry {
                width: w,
                height: h,
            },
            x: 0,
            y: 0,
            width: w,
            height: h,
        }
    }
    #[test]
    fn session_reconstruction_plan_never_compacts_ordinals_or_reuses_guide_photons() {
        let d = domain(8, 8);
        let maps = vec![FocusSummary {
            domain: d,
            frames: 10..20,
            ordinal: vec![4.; 64],
            width: vec![1.; 64],
            qualified: vec![true; 64],
        }];
        let mut placed = vec![true; 20];
        placed[14] = false;
        let plan = tiles(d, &maps, &placed, 8).unwrap();
        assert_eq!(plan.len(), 1);
        assert_eq!(plan[0].sources, vec![13, 15]);
        assert_eq!(plan[0].guides, vec![12, 16]);
        assert_eq!(maps[0].response(15, 0), (-0.5_f32).exp());
        assert_eq!(maps[0].response(17, 0), 0.);
    }
    #[test]
    fn session_reconstruction_plan_subdivides_complete_source_unions_or_retains_native() {
        let d = domain(64, 32);
        let map = FocusSummary {
            domain: d,
            frames: 0..100,
            ordinal: (0..d.pixels()).map(|i| 4. + (i % d.width) as f32).collect(),
            width: vec![1.; d.pixels()],
            qualified: vec![true; d.pixels()],
        };
        let plan = tiles(d, &[map], &[true; 100], 40).unwrap();
        assert!(plan.len() > 1);
        assert!(
            plan.iter()
                .all(|t| t.skip.is_none() && t.sources.len() + t.guides.len() <= 40)
        );
        let mut covered = vec![0_u8; d.pixels() * 4];
        for tile in plan {
            for y in tile.rect.y..tile.rect.y + tile.rect.height {
                for x in tile.rect.x..tile.rect.x + tile.rect.width {
                    covered[y * d.width * 2 + x] += 1;
                }
            }
        }
        assert!(covered.iter().all(|&n| n == 1));
        let broad = FocusSummary {
            domain: d,
            frames: 0..100,
            ordinal: vec![50.; d.pixels()],
            width: vec![45.; d.pixels()],
            qualified: vec![true; d.pixels()],
        };
        let plan = tiles(d, &[broad], &[true; 100], 40).unwrap();
        assert!(
            plan.iter()
                .all(|t| t.skip == Some(Skip::SourceBudget) && t.sources.is_empty())
        );
    }
    #[test]
    fn session_reconstruction_focus_rejects_same_length_in_a_different_gauge() {
        let mut d = domain(8, 8);
        d.full = strehl_core::plane::PlaneGeometry {
            width: 12,
            height: 12,
        };
        let map = FocusSummary {
            domain: SamplingDomain { x: 1, ..d },
            frames: 0..10,
            ordinal: vec![4.; 64],
            width: vec![1.; 64],
            qualified: vec![true; 64],
        };
        assert!(tiles(d, &[map], &[true; 10], 8).is_err());
        assert!(plan_bytes(d, usize::MAX, 10).is_err());
    }
    #[test]
    fn session_reconstruction_larger_cohort_cache_keeps_every_tile_and_original_identity() {
        let d = domain(192, 96);
        let maps: Vec<_> = [0, 100]
            .into_iter()
            .map(|offset| FocusSummary {
                domain: d,
                frames: offset..offset + 100,
                ordinal: (0..d.pixels())
                    .map(|p| 8. + ((p % d.width) / 12 + p / d.width / 16) as f32)
                    .collect(),
                width: vec![2.; d.pixels()],
                qualified: vec![true; d.pixels()],
            })
            .collect();
        let before = tiles(d, &maps, &[true; 200], MAX_SOURCES + 4).unwrap();
        let after = tiles(d, &maps, &[true; 200], 200).unwrap();
        assert_eq!(before.len(), after.len());
        for (a, b) in before.iter().zip(&after) {
            assert_eq!(
                (a.rect.x, a.rect.y, a.rect.width, a.rect.height),
                (b.rect.x, b.rect.y, b.rect.width, b.rect.height)
            );
            assert_eq!(a.sources, b.sources);
            assert_eq!(a.guides, b.guides);
            assert_eq!(a.skip, b.skip);
            assert!(b.sources.len() <= MAX_SOURCES);
        }
        assert!(after.iter().any(|tile| tile.sources.len() > 16));
    }
    #[test]
    fn session_reconstruction_plan_refusal_drops_broad_source_capacity_and_reserves_small_remainders()
     {
        let d = domain(35, 17);
        let frames = 2000;
        let broad = FocusSummary {
            domain: d,
            frames: 0..frames,
            ordinal: vec![1000.; d.pixels()],
            width: vec![1000.; d.pixels()],
            qualified: vec![true; d.pixels()],
        };
        let plan = tiles(d, &[broad], &vec![true; frames], 80).unwrap();
        assert_eq!(plan.len(), 8);
        assert!(plan.iter().all(|t| t.skip == Some(Skip::SourceBudget)
            && t.sources.capacity() == 0
            && t.guides.capacity() == 0));
        let retained = plan.capacity() * std::mem::size_of::<Tile>()
            + plan
                .iter()
                .map(|t| {
                    (t.sources.capacity() + t.guides.capacity()) * std::mem::size_of::<usize>()
                })
                .sum::<usize>();
        assert!(retained <= plan_bytes(d, 1, frames).unwrap());
    }
}
