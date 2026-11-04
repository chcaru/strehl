//! Exact strict-bilinear read/support sets in each original acquisition.
//! A set entry denotes one same-color plane cell; green luma denotes both
//! original green sites in that cell. No two cells share a CFA photosite.
use super::{Patch, Policy};
use crate::align::{Similarity, SimilarityParams, TileProbe};

#[derive(Clone)]
pub(super) struct Footprint {
    side: usize,
    pub(super) cells: [Vec<u8>; 2],
}
impl Footprint {
    pub(super) fn new(side: usize) -> Self {
        Self {
            side,
            cells: [vec![0; side * side], vec![0; side * side]],
        }
    }
    fn mark(&mut self, role: usize, x: isize, y: isize) {
        if x >= 0 && y >= 0 && x < self.side as isize && y < self.side as isize {
            self.cells[role][y as usize * self.side + x as usize] = 1;
        }
    }
    /// Finite Gaussian support, including clipping-mask dependencies. The
    /// dilation is separable but applies only to spatial axes within one source.
    pub(super) fn original(self, radius: usize) -> Self {
        if radius == 0 {
            return self;
        }
        let mut result = Self::new(self.side);
        let mut horizontal = vec![0u8; self.side * self.side];
        for role in 0..2 {
            horizontal.fill(0);
            for y in 0..self.side {
                for x in 0..self.side {
                    if self.cells[role][y * self.side + x] != 0 {
                        let lo = x.saturating_sub(radius);
                        let hi = (x + radius + 1).min(self.side);
                        horizontal[y * self.side + lo..y * self.side + hi].fill(1);
                    }
                }
            }
            for y in 0..self.side {
                for x in 0..self.side {
                    if horizontal[y * self.side + x] != 0 {
                        for yy in y.saturating_sub(radius)..(y + radius + 1).min(self.side) {
                            result.cells[role][yy * self.side + x] = 1;
                        }
                    }
                }
            }
        }
        result
    }
    pub(super) fn union(&mut self, other: &Self) {
        for (a, b) in self.cells.iter_mut().zip(&other.cells) {
            for (x, y) in a.iter_mut().zip(b) {
                *x |= *y;
            }
        }
    }
    pub(super) fn packed(&self) -> [Vec<u64>; 2] {
        std::array::from_fn(|role| {
            let mut words = vec![0u64; self.cells[role].len().div_ceil(64)];
            for (i, v) in self.cells[role].iter().enumerate() {
                if *v != 0 {
                    words[i / 64] |= 1u64 << (i % 64);
                }
            }
            words
        })
    }
    pub(super) fn overlaps(&self, other: &Self) -> bool {
        self.cells
            .iter()
            .zip(&other.cells)
            .any(|(a, b)| a.iter().zip(b).any(|(x, y)| *x != 0 && *y != 0))
    }
}
pub(super) fn probe(spot: (usize, usize), t: Similarity, side: usize, policy: Policy) -> TileProbe {
    let x = spot.0 as f64 + policy.tile_quad as f64 * 0.5;
    let y = spot.1 as f64 + policy.tile_quad as f64 * 0.5;
    let moved = t.apply_at(x, y, side as f64 * 0.5, side as f64 * 0.5);
    TileProbe {
        tx: spot.0,
        ty: spot.1,
        size: policy.tile_quad,
        predicted: ((moved.0 - x) as f32, (moved.1 - y) as f32),
        radius: policy.radius_quad,
    }
}
/// Enumerate an upper bound of every numerical/support read by this probe:
/// the reference information rectangle (including central derivatives), then
/// ALL four bilinear taps for the entire moving search patch, including taps
/// whose interpolation coefficient is zero. The f32 predicted centre is exactly
/// the one actually consumed by ncc_tile_warped. Low-contrast/early-OOB paths
/// may read fewer sites; retaining the superset is deliberately conservative.
pub(super) fn visit(
    reference: &Patch,
    moving: &Patch,
    p: TileProbe,
    warp: SimilarityParams,
    mut footprint: Option<&mut Footprint>,
) -> bool {
    let mut valid = true;
    let mut tap = |role: usize, x: isize, y: isize| {
        let patch = if role == 0 { reference } else { moving };
        if let Some(f) = footprint.as_deref_mut() {
            f.mark(role, x, y);
        }
        if x < 0
            || y < 0
            || x >= patch.geometry.width as isize
            || y >= patch.geometry.height as isize
            || !patch.valid[y as usize * patch.geometry.width + x as usize]
        {
            valid = false;
        }
    };
    for y in p.ty as isize - 1..=(p.ty + p.size) as isize {
        for x in p.tx as isize - 1..=(p.tx + p.size) as isize {
            tap(0, x, y);
        }
    }
    let half = p.size as f64 * 0.5;
    let mcx = p.tx as f64 + half + f64::from(p.predicted.0);
    let mcy = p.ty as f64 + half + f64::from(p.predicted.1);
    let ar = 1. + warp.g;
    let ai = warp.rot;
    let n = p.size + 2 * p.radius as usize;
    for q in 0..n {
        let vy = q as f64 - f64::from(p.radius) - half;
        for u in 0..n {
            let vx = u as f64 - f64::from(p.radius) - half;
            let sx = mcx + ar * vx - ai * vy;
            let sy = mcy + ai * vx + ar * vy;
            if !sx.is_finite()
                || !sy.is_finite()
                || sx < 0.
                || sy < 0.
                || sx >= (moving.geometry.width - 1) as f64
                || sy >= (moving.geometry.height - 1) as f64
            {
                return false;
            }
            let x = sx.floor() as isize;
            let y = sy.floor() as isize;
            // Strict sampler always reads these four sites, even at integers.
            for dy in 0..=1 {
                for dx in 0..=1 {
                    tap(1, x + dx, y + dy);
                }
            }
        }
    }
    valid
}
