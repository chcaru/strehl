//! Explicit source-range repairs, rebuilt in the original output gauge.
//!
//! A separate accumulator is essential: multiplying selected band weights in
//! the ordinary merge would still admit excluded sources through the mean
//! fallback, the base residual, and the reconstruction hull. Here all those
//! quantities are built exclusively from the permitted, placed source frames.
//! The finished CFA repair is feathered before colour development. This is a
//! manual source constraint, not automatic artifact recognition.
use super::*;
use strehl_edit::{DevelopmentRecipe, RegionAdjustment};

pub(super) struct Repairs {
    recipe: Option<DevelopmentRecipe>,
}

pub(super) struct RepairContext<'a, S> {
    pub source: &'a S,
    pub domain: PyramidDomain,
    pub config: MergeConfig,
    pub levels: Levels,
    pub noise: &'a NoiseModel,
    pub warps: Option<&'a WarpMap>,
    pub defect: Option<(&'a crate::stack::DefectPlan, &'a crate::stack::DefectTally)>,
    pub per_chunk: usize,
    pub progress: Option<&'a crate::ui_progress::Progress>,
}

impl Repairs {
    pub(super) fn load(path: Option<&Path>) -> Result<Self> {
        let Some(path) = path else { return Ok(Self { recipe: None }); };
        ensure!(std::fs::metadata(path)?.len() <= 1_048_576, "region recipe exceeds 1 MiB");
        let text = std::fs::read_to_string(path).context("reading source-region recipe")?;
        let recipe: DevelopmentRecipe = serde_json::from_str(&text).context("parsing source-region recipe")?;
        recipe.validate()?;
        Ok(Self { recipe: Some(recipe) })
    }

    fn regions(&self) -> impl Iterator<Item = &RegionAdjustment> {
        self.recipe.iter().flat_map(|r| &r.regions)
            .filter(|r| r.enabled && r.source_range.is_some())
    }

    pub(super) fn active(&self) -> bool {
        self.regions().next().is_some()
    }

    /// Only use after apply succeeds. A master records what was actually
    /// reconstructed, not an annotation whose range has not been consumed.
    pub(super) fn applied_recipe(&self) -> Option<&DevelopmentRecipe> {
        self.active().then_some(self.recipe.as_ref()).flatten()
    }

    pub(super) fn preflight(
        &self,
        count: usize,
        domain: PyramidDomain,
        warps: Option<&WarpMap>,
        fit: Option<align_cmd::CoverFit>,
    ) -> Result<()> {
        if !self.active() { return Ok(()); }
        // This pass must not turn missing image coverage into a black patch.
        // The existing coverage solve certifies the complete analysis domain;
        // do not guess a regional footprint from an uncovered global result.
        ensure!(
            warps.is_none() || matches!(fit, Some(align_cmd::CoverFit::Scaled(_)
                | align_cmd::CoverFit::Cropped { .. })),
            "source-region repairs require covered alignment; use --cover scale or crop",
        );
        if let Some(map) = warps {
            ensure!(map.geometry() == domain.full, "repair placement gauge differs from the original image");
        }
        for r in self.regions() {
            let range = r.source_range.as_ref().unwrap();
            ensure!(range.last < count, "region {:?} asks for frame {}, but the stack contains {count} frames (zero-based indices)", r.name, range.last);
            let mut placed = 0;
            for index in range.first..=range.last {
                if warps.map_or(Ok(true), |m| m.warp(index).map(|w| matches!(w, FrameWarp::Placed(_))))? {
                    placed += 1;
                }
            }
            ensure!(placed > 0, "region {:?} has no permitted placed source frames", r.name);
            ensure!(has_samples(r, domain.analysis()), "region {:?} contains no output sample centers; enlarge it", r.name);
        }
        Ok(())
    }

    pub(super) fn apply(
        &self,
        original: &mut [Vec<f32>],
        cx: RepairContext<'_, impl PyramidFrameSource>,
    ) -> Result<()> {
        if !self.active() { return Ok(()); }
        let geom = cx.domain.analysis();
        ensure!(cx.per_chunk > 0, "repair canonical chunk size is zero");
        ensure!(original.len() == BAND_PLANES && original.iter().all(|p| p.len() == geom.pixels()),
            "source repair must use the original reconstructed CFA geometry");
        let region_count = self.regions().count();
        for (region_index, region) in self.regions().enumerate() {
            let range = region.source_range.as_ref().unwrap();
            ensure!(range.last < cx.source.len(), "repair source range exceeds the source count");
            eprintln!(
                "source repair   : {:?}, frames {}..={} (zero-based), feather {:.3}; \
                 extra restricted-source pass in the original output gauge",
                region.name, range.first, range.last, region.feather,
            );
            let start = Instant::now();
            let mut worker = BandWorker::new(cx.domain, cx.config);
            let mut merged: Option<BandMerge> = None;
            let mut accepted = 0;
            let mut completed = 0;
            if let Some(progress) = cx.progress {
                progress.source_repair(region_index, region_count, range.first, range.last,
                    range.first, 0, 0, "started");
            }
            // Keep the full stack's canonical boundaries. No excluded donor is
            // decoded or folded, including the fallback/base/hull pathways.
            for begin in (0..cx.source.len()).step_by(cx.per_chunk) {
                let end = (begin + cx.per_chunk).min(cx.source.len());
                let first = begin.max(range.first);
                let last = end.min(range.last + 1);
                if first >= last { continue; }
                worker.reset_chunk();
                let mut folded = 0;
                for index in first..last {
                    if worker.fold(cx.source, index, cx.levels, cx.noise, cx.warps, cx.defect)? {
                        folded += 1;
                    }
                    completed += 1;
                    if let Some(progress) = cx.progress {
                        progress.source_repair(region_index, region_count, range.first, range.last,
                            index, completed, accepted + folded, "folded");
                    }
                }
                if folded == 0 { continue; }
                accepted += folded;
                match merged.as_mut() {
                    Some(acc) => acc.absorb(&worker.merge),
                    None => {
                        merged = Some(std::mem::replace(&mut worker.merge,
                            BandMerge::new(geom.width, geom.height, BAND_PLANES, cx.config)));
                    }
                }
            }
            drop(worker);
            ensure!(accepted > 0, "region {:?} has no permitted placed source frames", region.name);
            let merge = merged.context("region repair produced no accumulator")?;
            let repaired = merge.finish(&mut Workspace::new(merge.sizes()));
            drop(merge);
            blend(original, &repaired, geom, region)?;
            if let Some(progress) = cx.progress {
                progress.source_repair(region_index, region_count, range.first, range.last,
                    range.last, completed, accepted, "finished");
            }
            eprintln!("source repair   : {:?}, {accepted} placed frames, {:.2} s; \
                source-only fallback and original alignment retained", region.name,
                start.elapsed().as_secs_f64());
        }
        Ok(())
    }
}

fn uv(x: usize, y: usize, c: usize, geom: PlaneGeometry) -> [f32; 2] {
    // RGGB site centres in the final image, not coordinates in a newly cropped
    // ROI or in a source camera frame. This also matches binned geometry in
    // the limit; individual CFA sites differ by at most half an output pixel.
    [
        (2 * x + (c % 2)) as f32 / (2 * geom.width) as f32 + 0.25 / geom.width as f32,
        (2 * y + (c / 2)) as f32 / (2 * geom.height) as f32 + 0.25 / geom.height as f32,
    ]
}

fn has_samples(region: &RegionAdjustment, geom: PlaneGeometry) -> bool {
    let (min, max) = region.shape.bounds();
    let x0 = (min[0] * geom.width as f32).floor().max(0.0) as usize;
    let y0 = (min[1] * geom.height as f32).floor().max(0.0) as usize;
    let x1 = (max[0] * geom.width as f32).ceil().min(geom.width as f32) as usize;
    let y1 = (max[1] * geom.height as f32).ceil().min(geom.height as f32) as usize;
    (y0..y1).any(|y| (x0..x1).any(|x|
        (0..BAND_PLANES).any(|c| region.shape.weight(uv(x, y, c, geom), region.feather) > 0.0)))
}

fn blend(
    original: &mut [Vec<f32>],
    repaired: &[Vec<f32>],
    geom: PlaneGeometry,
    region: &RegionAdjustment,
) -> Result<()> {
    ensure!(repaired.len() == BAND_PLANES && repaired.iter().all(|p| p.len() == geom.pixels()),
        "repair reconstruction changed the output geometry");
    ensure!(repaired.iter().flatten().all(|v| v.is_finite()),
        "repair reconstruction contains nonfinite values");
    for (c, (dst, src)) in original.iter_mut().zip(repaired).enumerate() {
        dst.par_iter_mut().zip(src).enumerate().for_each(|(i, (v, &r))| {
            let w = region.shape.weight(uv(i % geom.width, i / geom.width, c, geom), region.feather);
            if w >= 1.0 {
                *v = r;
            } else if w > 0.0 && v.to_bits() != r.to_bits() {
                *v += (r - *v) * w;
            }
        });
    }
    Ok(())
}
