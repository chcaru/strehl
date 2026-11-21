//! Region culling and layer order, prepared once per render.
//!
//! `DevelopmentRecipe::apply_pixel` visits every region for every pixel. A
//! prepared recipe keeps each region's bounding box (and, for strokes, boxes
//! over runs of segments) so a pixel outside a region skips it. Skipping is
//! exact: outside its box a region's weight is 0, and `Adjustments::apply`
//! returns its input unchanged at amount 0, so the result is bit-identical.
use super::{Adjustments, DevelopmentRecipe, RegionShape};

/// Bounding boxes are grown by this much (normalized units, about 0.07 px on
/// a 7000 px photograph) so rounding can never cull a pixel of nonzero weight.
const CULL_MARGIN: f32 = 1e-5;
/// Segments per stroke box.
const STROKE_RUN: usize = 16;

/// Distance, in brush radii, from `p` to the segment `a`-`b`. Returns infinity
/// outside the segment's box grown by one radius, where the distance exceeds 1
/// and the segment cannot contribute.
#[inline]
pub(crate) fn segment_distance(a: [f32; 2], b: [f32; 2], r: [f32; 2], p: [f32; 2]) -> f32 {
    let (lo, hi) = segment_box(a, b, r);
    if p[0] < lo[0] || p[0] > hi[0] || p[1] < lo[1] || p[1] > hi[1] {
        return f32::INFINITY;
    }
    let ax = (p[0] - a[0]) / r[0];
    let ay = (p[1] - a[1]) / r[1];
    let dx = (b[0] - a[0]) / r[0];
    let dy = (b[1] - a[1]) / r[1];
    let len2 = dx * dx + dy * dy;
    let t = if len2 > 0.0 {
        ((ax * dx + ay * dy) / len2).clamp(0.0, 1.0)
    } else {
        0.0
    };
    (ax - t * dx).hypot(ay - t * dy)
}

#[inline]
fn segment_box(a: [f32; 2], b: [f32; 2], r: [f32; 2]) -> ([f32; 2], [f32; 2]) {
    (
        [a[0].min(b[0]) - r[0], a[1].min(b[1]) - r[1]],
        [a[0].max(b[0]) + r[0], a[1].max(b[1]) + r[1]],
    )
}

/// A stroke of one point is a single dab; otherwise one segment per pair.
#[inline]
pub(crate) fn stroke_segments(points: &[[f32; 2]]) -> usize {
    points
        .len()
        .saturating_sub(1)
        .max(usize::from(!points.is_empty()))
}

#[inline]
pub(crate) fn stroke_segment(points: &[[f32; 2]], i: usize) -> ([f32; 2], [f32; 2]) {
    (points[i], points[(i + 1).min(points.len() - 1)])
}

pub(crate) fn stroke_distance(points: &[[f32; 2]], r: [f32; 2], p: [f32; 2]) -> f32 {
    (0..stroke_segments(points))
        .map(|i| {
            let (a, b) = stroke_segment(points, i);
            segment_distance(a, b, r, p)
        })
        .fold(f32::INFINITY, f32::min)
}

/// Shared feather tail of every shape's weight.
#[inline]
pub(crate) fn feathered(d: f32, feather: f32) -> f32 {
    if d <= 0.0 {
        return 0.0;
    }
    if feather <= 0.0 {
        return 1.0;
    }
    let t = (d / feather).clamp(0.0, 1.0);
    t * t * (3.0 - 2.0 * t)
}

impl RegionShape {
    /// Unclamped box outside which the weight is 0, grown by `CULL_MARGIN`.
    pub fn cull_box(&self) -> ([f32; 2], [f32; 2]) {
        let (lo, hi) = match self {
            Self::Ellipse { center, radius } => (
                [center[0] - radius[0], center[1] - radius[1]],
                [center[0] + radius[0], center[1] + radius[1]],
            ),
            Self::Rectangle { min, max } => (*min, *max),
            Self::Polygon { points } => points_box(points, [0.0; 2]),
            Self::Stroke { points, radius } => points_box(points, *radius),
        };
        (
            [lo[0] - CULL_MARGIN, lo[1] - CULL_MARGIN],
            [hi[0] + CULL_MARGIN, hi[1] + CULL_MARGIN],
        )
    }

    /// Constant-time rejection for shapes whose box costs nothing to compute.
    /// Polygons and strokes reject inside their own weight evaluation.
    #[inline]
    pub(crate) fn cheap_reject(&self, uv: [f32; 2]) -> bool {
        match self {
            Self::Ellipse { .. } | Self::Rectangle { .. } => !inside(self.cull_box(), uv),
            Self::Polygon { .. } | Self::Stroke { .. } => false,
        }
    }

    /// The weight evaluator for repeated use, bit-identical to `weight`.
    pub fn prepare(&self) -> PreparedShape<'_> {
        let runs = match self {
            Self::Stroke { points, radius } => {
                let segments = stroke_segments(points);
                (0..segments)
                    .step_by(STROKE_RUN)
                    .map(|start| {
                        let end = (start + STROKE_RUN).min(segments);
                        let mut lo = [f32::INFINITY; 2];
                        let mut hi = [f32::NEG_INFINITY; 2];
                        for i in start..end {
                            let (a, b) = stroke_segment(points, i);
                            let (l, h) = segment_box(a, b, *radius);
                            for c in 0..2 {
                                lo[c] = lo[c].min(l[c]);
                                hi[c] = hi[c].max(h[c]);
                            }
                        }
                        StrokeRun { lo, hi, start, end }
                    })
                    .collect()
            }
            _ => Vec::new(),
        };
        PreparedShape {
            shape: self,
            cull: self.cull_box(),
            runs,
        }
    }

    /// A brush path as a stroke: simplified to a tenth of the radius and
    /// thinned further if needed to respect `MAX_STROKE_POINTS`.
    pub fn stroke_from_path(path: &[[f32; 2]], radius: [f32; 2]) -> Self {
        let clamped: Vec<[f32; 2]> = path
            .iter()
            .filter(|p| p[0].is_finite() && p[1].is_finite())
            .map(|p| [p[0].clamp(0.0, 1.0), p[1].clamp(0.0, 1.0)])
            .collect();
        let radius = radius.map(|r| {
            if r.is_finite() {
                r.clamp(0.0001, 0.5)
            } else {
                0.0001
            }
        });
        let mut tolerance = 0.1f32;
        let mut points = simplify(&clamped, radius, tolerance);
        while points.len() > super::MAX_STROKE_POINTS {
            tolerance *= 2.0;
            points = simplify(&clamped, radius, tolerance);
        }
        Self::Stroke { points, radius }
    }
}

fn points_box(points: &[[f32; 2]], grow: [f32; 2]) -> ([f32; 2], [f32; 2]) {
    let mut lo = [f32::INFINITY; 2];
    let mut hi = [f32::NEG_INFINITY; 2];
    for p in points {
        for c in 0..2 {
            lo[c] = lo[c].min(p[c] - grow[c]);
            hi[c] = hi[c].max(p[c] + grow[c]);
        }
    }
    (lo, hi)
}

#[inline]
fn inside((lo, hi): ([f32; 2], [f32; 2]), uv: [f32; 2]) -> bool {
    uv[0] >= lo[0] && uv[0] <= hi[0] && uv[1] >= lo[1] && uv[1] <= hi[1]
}

/// Ramer-Douglas-Peucker in brush-radius units; keeps both end points.
fn simplify(points: &[[f32; 2]], r: [f32; 2], tolerance: f32) -> Vec<[f32; 2]> {
    if points.len() <= 2 {
        let mut out = points.to_vec();
        out.dedup();
        return out;
    }
    let mut keep = vec![false; points.len()];
    keep[0] = true;
    keep[points.len() - 1] = true;
    let mut stack = vec![(0usize, points.len() - 1)];
    while let Some((first, last)) = stack.pop() {
        let (a, b) = (points[first], points[last]);
        let mut worst = (0.0f32, first);
        for (i, &p) in points.iter().enumerate().take(last).skip(first + 1) {
            let d = segment_distance(a, b, r, p);
            // Outside the grown box the distance is over one radius: always keep.
            let d = if d.is_finite() { d } else { f32::MAX };
            if d > worst.0 {
                worst = (d, i);
            }
        }
        if worst.0 > tolerance {
            keep[worst.1] = true;
            stack.push((first, worst.1));
            stack.push((worst.1, last));
        }
    }
    let mut out: Vec<[f32; 2]> = points
        .iter()
        .zip(keep)
        .filter_map(|(&p, k)| k.then_some(p))
        .collect();
    out.dedup();
    out
}

struct StrokeRun {
    lo: [f32; 2],
    hi: [f32; 2],
    start: usize,
    end: usize,
}

/// A shape with its culling data computed once.
pub struct PreparedShape<'a> {
    shape: &'a RegionShape,
    cull: ([f32; 2], [f32; 2]),
    runs: Vec<StrokeRun>,
}

impl PreparedShape<'_> {
    /// False only where the weight is certainly 0.
    #[inline]
    pub fn may_contain(&self, uv: [f32; 2]) -> bool {
        inside(self.cull, uv)
    }

    /// Bit-identical to `RegionShape::weight`.
    #[inline]
    pub fn weight(&self, uv: [f32; 2], feather: f32) -> f32 {
        if !self.may_contain(uv) {
            return 0.0;
        }
        match self.shape {
            RegionShape::Stroke { points, radius } => {
                let mut best = f32::INFINITY;
                for run in &self.runs {
                    if !inside((run.lo, run.hi), uv) {
                        continue;
                    }
                    for i in run.start..run.end {
                        let (a, b) = stroke_segment(points, i);
                        best = best.min(segment_distance(a, b, *radius, uv));
                    }
                }
                feathered(1.0 - best, feather)
            }
            shape => shape.weight(uv, feather),
        }
    }
}

enum SpatialTarget {
    Global,
    Region(usize),
    Missing,
}

struct PreparedRegion<'a> {
    tone: bool,
    feather: f32,
    shape: PreparedShape<'a>,
}

/// A recipe ready for per-pixel use in a loop. Build once per render.
pub struct PreparedRecipe<'a> {
    recipe: &'a DevelopmentRecipe,
    order: Vec<usize>,
    regions: Vec<PreparedRegion<'a>>,
    spatial: Vec<SpatialTarget>,
}

impl<'a> PreparedRecipe<'a> {
    pub fn new(recipe: &'a DevelopmentRecipe) -> Self {
        let neutral = Adjustments::default();
        let regions = recipe
            .regions
            .iter()
            .map(|r| PreparedRegion {
                tone: r.enabled && r.adjustments != neutral,
                feather: r.feather,
                shape: r.shape.prepare(),
            })
            .collect();
        let spatial = recipe
            .spatial
            .iter()
            .map(|t| match t.target_region.as_deref() {
                None => SpatialTarget::Global,
                Some(id) => recipe
                    .regions
                    .iter()
                    .position(|r| r.id == id && r.enabled)
                    .map_or(SpatialTarget::Missing, SpatialTarget::Region),
            })
            .collect();
        Self {
            recipe,
            order: recipe.application_order(),
            regions,
            spatial,
        }
    }

    pub fn recipe(&self) -> &'a DevelopmentRecipe {
        self.recipe
    }

    /// Bit-identical to `DevelopmentRecipe::apply_pixel`.
    pub fn apply_pixel(&self, rgb: [f32; 3], uv: [f32; 2]) -> [f32; 3] {
        let mut v = self.recipe.global.apply(rgb, 1.0);
        for &i in &self.order {
            let region = &self.regions[i];
            if region.tone && region.shape.may_contain(uv) {
                v = self.recipe.regions[i]
                    .adjustments
                    .apply(v, region.shape.weight(uv, region.feather));
            }
        }
        for (treatment, target) in self.recipe.spatial.iter().zip(&self.spatial) {
            let weight = match *target {
                SpatialTarget::Global => 1.0,
                SpatialTarget::Missing => 0.0,
                SpatialTarget::Region(i) => {
                    let region = &self.regions[i];
                    region.shape.weight(uv, region.feather)
                }
            };
            v = treatment.apply(v, uv, weight);
        }
        v
    }
}

/// Anything that develops one pixel: a recipe, or a recipe prepared for a loop.
pub(crate) trait PixelRecipe: Sync {
    fn pixel(&self, rgb: [f32; 3], uv: [f32; 2]) -> [f32; 3];
}

impl PixelRecipe for DevelopmentRecipe {
    #[inline]
    fn pixel(&self, rgb: [f32; 3], uv: [f32; 2]) -> [f32; 3] {
        self.apply_pixel(rgb, uv)
    }
}

impl PixelRecipe for PreparedRecipe<'_> {
    #[inline]
    fn pixel(&self, rgb: [f32; 3], uv: [f32; 2]) -> [f32; 3] {
        self.apply_pixel(rgb, uv)
    }
}

#[cfg(test)]
#[path = "recipe-prepared-tests.rs"]
mod tests;
