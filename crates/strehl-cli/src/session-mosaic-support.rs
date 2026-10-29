//! Check the footprints actually consumed by every native/coarse search pass.
//! Nominal feature radii nominate work; these observed footprints determine
//! whether an accepted measurement really respected spatial holdout roles.
use super::*;
use rayon::prelude::*;
use strehl_core::align::PairTrace;

#[derive(Clone, Copy)]
pub(super) struct RoleWitness<'a> {
    source: PlaneGeometry,
    inverse: Similarity,
    guide_origin: [f64; 2],
    guide_step: usize,
    block_side: usize,
    heldout: bool,
    filter_halo: usize,
    pass: usize,
    plan: Option<&'a super::super::roles::FrozenRolePlan>,
    island: Option<usize>,
}
impl<'a> RoleWitness<'a> {
    pub(super) fn new(
        guide: &super::super::MosaicGuide,
        placement: Similarity,
        heldout: bool,
        config: &'a MosaicGeometryConfig,
    ) -> Result<Self> {
        Ok(Self {
            source: guide.source_geometry,
            inverse: placement.invert().context("singular support gauge")?,
            guide_origin: guide.origin,
            guide_step: guide.step,
            block_side: config.holdout_block_guide_pixels,
            heldout,
            pass: guide.pass,
            plan: config.role_plan.as_deref(),
            island: None,
            filter_halo: if config.native_lowpass {
                native_filter::HALO
            } else {
                0
            },
        })
    }
    pub(super) fn for_island(mut self, island: Option<usize>) -> Self {
        self.island = island;
        self
    }
    /// Raw quad ownership precedes filtering. The query observer separately
    /// expands by the filter halo, so it cannot certify a zeroed boundary tap.
    fn raw_quad(self, x: usize, y: usize) -> bool {
        Self {
            filter_halo: 0,
            ..self
        }
        .rectangle(&[[x as f64, y as f64]], 0.0, 1)
    }
    pub(super) fn rectangle(self, points: &[[f64; 2]], expand: f64, factor: usize) -> bool {
        let offset = (factor - 1) as f64 * 0.5;
        let extension = expand * factor as f64 + offset + 0.5 + self.filter_halo as f64;
        let mut low = [f64::INFINITY; 2];
        let mut high = [f64::NEG_INFINITY; 2];
        for p in points {
            for dy in [-extension, extension] {
                for dx in [-extension, extension] {
                    let native = [
                        p[0] * factor as f64 + offset + dx,
                        p[1] * factor as f64 + offset + dy,
                    ];
                    let anchor = point(self.inverse, native, self.source);
                    for axis in 0..2 {
                        let q = (anchor[axis] - self.guide_origin[axis]) / self.guide_step as f64;
                        low[axis] = low[axis].min(q);
                        high[axis] = high[axis].max(q);
                    }
                }
            }
        }
        let center = [(low[0] + high[0]) * 0.5, (low[1] + high[1]) * 0.5];
        let radius = ((high[0] - low[0]).max(high[1] - low[1]) * 0.5) + 1e-6;
        if let Some(frozen) = self.plan {
            let bounds = super::super::roles::Rectangle {
                low: [0, 1]
                    .map(|axis| self.guide_origin[axis] + self.guide_step as f64 * low[axis]),
                high: [0, 1]
                    .map(|axis| self.guide_origin[axis] + self.guide_step as f64 * high[axis]),
            };
            return match frozen.plan.classify(self.pass, bounds) {
                Some(super::super::roles::SpatialRole::Fit) => !self.heldout,
                Some(super::super::roles::SpatialRole::Heldout(island)) => {
                    self.heldout && self.island == Some(island)
                }
                None => false,
            };
        }
        super::super::matching::reserved_role(center, radius, self.block_side)
            .is_some_and(|(_, heldout)| heldout == self.heldout)
    }
}
/// Identical green arithmetic on allowed quads; other roles are never read.
/// The geometric mask is fixed before any signal statistics, box reduction,
/// filtering or matching. Zeros are not validity: observed support must still
/// pass the independent role and original-pixel witnesses before admission.
pub(super) fn green_luma_reserved<S: QuadSource + Sync>(
    source: &S,
    black: f32,
    role: RoleWitness<'_>,
    output: &mut [f32],
) {
    let g = source.geometry();
    assert_eq!(output.len(), g.pixels());
    let (g1x, g1y) = strehl_core::CfaPlane::G1.rggb_offset();
    let (g2x, g2y) = strehl_core::CfaPlane::G2.rggb_offset();
    output
        .par_chunks_mut(g.width)
        .enumerate()
        .for_each(|(y, row)| {
            let (row0, row1) = source.quad_rows(y);
            let first = if g1y == 0 { row0 } else { row1 };
            let second = if g2y == 0 { row0 } else { row1 };
            for (x, value) in row.iter_mut().enumerate() {
                *value = if role.raw_quad(x, y) {
                    let g1 = (first[2 * x + g1x] as f32 - black).max(0.0);
                    let g2 = (second[2 * x + g2x] as f32 - black).max(0.0);
                    0.5 * (g1 + g2)
                } else {
                    0.0
                };
            }
        });
}
#[derive(Clone, Copy)]
pub(super) struct PixelWitness<'a> {
    pub source: &'a dyn QuadSource,
    pub white: f32,
    pub filter_halo: usize,
}
impl PixelWitness<'_> {
    pub(super) fn rectangle(self, points: &[[f64; 2]], expand: f64, factor: usize) -> bool {
        let g = self.source.geometry();
        // A downsampled value is a complete factor-by-factor native box.
        // Moving-plane bilinear interpolation adds its full one-pixel support.
        let mut low = [f64::INFINITY; 2];
        let mut high = [f64::NEG_INFINITY; 2];
        for p in points {
            for axis in 0..2 {
                let first = p[axis].floor() * factor as f64;
                low[axis] = low[axis].min(first - self.filter_halo as f64);
                high[axis] = high[axis].max(
                    first
                        + if expand > 0.0 { factor as f64 } else { 0.0 }
                        + (factor - 1) as f64
                        + self.filter_halo as f64,
                );
            }
        }
        if !low.into_iter().chain(high).all(f64::is_finite)
            || low[0] < 0.0
            || low[1] < 0.0
            || high[0].ceil() >= g.width as f64
            || high[1].ceil() >= g.height as f64
        {
            return false;
        }
        for y in low[1].floor() as usize..=high[1].ceil() as usize {
            let (r0, r1) = self.source.quad_rows(y);
            if r0.len() < 2 * g.width || r1.len() < 2 * g.width {
                return false;
            }
            for x in low[0].floor() as usize..=high[0].ceil() as usize {
                if f32::from(r0[2 * x + 1]) >= self.white || f32::from(r1[2 * x]) >= self.white {
                    return false;
                }
            }
        }
        true
    }
}
pub(super) fn reserved(trace: &PairTrace, roles: &[RoleWitness<'_>; 2], factor: usize) -> bool {
    observed_support(trace, Some(roles), None, factor)
}
pub(super) fn observed_support(
    trace: &PairTrace,
    roles: Option<&[RoleWitness<'_>; 2]>,
    pixels: Option<&[PixelWitness<'_>; 2]>,
    factor: usize,
) -> bool {
    if factor == 0 {
        return false;
    }
    for pass in &trace.fine_passes {
        let stage = &pass.stage.measurements;
        let Some(seed) = stage.seed else {
            return false;
        };
        if !stage.warped_tiles_used {
            return false;
        }
        let warp = Similarity::from_params(seed);
        for tile in &stage.tiles {
            let p = tile.probe;
            let (x0, y0, x1, y1) = (
                p.tx as f64,
                p.ty as f64,
                (p.tx + p.size - 1) as f64,
                (p.ty + p.size - 1) as f64,
            );
            let reference = [[x0, y0], [x0, y1], [x1, y0], [x1, y1]];
            if roles.is_some_and(|r| !r[0].rectangle(&reference, 0.0, factor))
                || pixels.is_some_and(|p| !p[0].rectangle(&reference, 0.0, factor))
            {
                return false;
            }
            let r = f64::from(p.radius);
            let half = p.size as f64 * 0.5;
            let moving_center = [
                p.tx as f64 + half + f64::from(p.predicted.0),
                p.ty as f64 + half + f64::from(p.predicted.1),
            ];
            let moving = [
                [x0 - r, y0 - r],
                [x0 - r, y1 + r],
                [x1 + r, y0 - r],
                [x1 + r, y1 + r],
            ]
            .map(|p| {
                // Match ncc_tile_warped's actual f32 predicted tile centre.
                // Re-evaluating the global f64 seed can differ near a boundary.
                let x = p[0] - (x0 + half);
                let y = p[1] - (y0 + half);
                [
                    moving_center[0] + warp.a.re * x - warp.a.im * y,
                    moving_center[1] + warp.a.im * x + warp.a.re * y,
                ]
            });
            if roles.is_some_and(|r| !r[1].rectangle(&moving, 1.0, factor))
                || pixels.is_some_and(|p| !p[1].rectangle(&moving, 1.0, factor))
            {
                return false;
            }
        }
    }
    !trace.fine_passes.is_empty()
}

#[cfg(test)]
mod halo_tests {
    use super::*;
    #[test]
    fn native_filter_halo_cannot_cross_reserved_role_or_hide_clipped_original() {
        let role = RoleWitness {
            source: PlaneGeometry {
                width: 512,
                height: 512,
            },
            inverse: Similarity::IDENTITY,
            guide_origin: [0.0; 2],
            guide_step: 1,
            block_side: 128,
            heldout: false,
            filter_halo: 0,
            pass: 0,
            plan: None,
            island: None,
        };
        assert!(role.rectangle(&[[130.0, 64.0]], 0.0, 1));
        assert!(
            !RoleWitness {
                filter_halo: 2,
                ..role
            }
            .rectangle(&[[130.0, 64.0]], 0.0, 1)
        );
        struct Original {
            pixels: Vec<u16>,
        }
        impl QuadSource for Original {
            fn geometry(&self) -> PlaneGeometry {
                PlaneGeometry {
                    width: 32,
                    height: 32,
                }
            }
            fn quad_rows(&self, y: usize) -> (&[u16], &[u16]) {
                let p = 2 * y * 64;
                (&self.pixels[p..p + 64], &self.pixels[p + 64..p + 128])
            }
        }
        let mut original = Original {
            pixels: vec![1000; 4096],
        };
        original.pixels[2 * 16 * 64 + 2 * 18 + 1] = 16000;
        let unfiltered = PixelWitness {
            source: &original,
            white: 16000.0,
            filter_halo: 0,
        };
        assert!(unfiltered.rectangle(&[[16.0, 16.0]], 0.0, 1));
        assert!(
            !PixelWitness {
                filter_halo: 2,
                ..unfiltered
            }
            .rectangle(&[[16.0, 16.0]], 0.0, 1)
        );
    }
}
