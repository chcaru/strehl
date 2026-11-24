//! Four-shot pixel-shift groups: geometry check, green witness and assembly.
//!
//! A group is four RAWs of one focal plane taken with the sensor moved by whole
//! photosites between them, so that every scene site is sampled once in red,
//! once in blue and twice in green. Nothing here resamples a Bayer member: a
//! group is used only when its measured member offsets are integers that cover
//! all four CFA parities, and is otherwise reported for demotion.
//!
//! # Coordinates
//!
//! Every member is addressed in its own **active-area** coordinates. A
//! member's offset `o_k` is defined so that member `k`'s photosite
//! `(x + o_k.x, y + o_k.y)` sees the scene point member 1's photosite `(x, y)`
//! sees. Member 1's offset is `(0, 0)`. Offsets are **measured on every group**
//! ([`register`]); no table is compiled in.
//!
//! # The green witness
//!
//! With offset parities `{(0,0),(1,0),(0,1),(1,1)}`, the photosite member `k`
//! puts on site `(x, y)` has CFA colour `cfa(x + o.x, y + o.y)` (RGGB). Green
//! lands from the two members whose `o.x + o.y` parity makes `x + y + o.x + o.y`
//! odd, and those two members differ by a diagonal step: one G1-type and one
//! G2-type photosite seeing the same scene point, with no interpolation. Their
//! difference is pure noise for a static, registered, flicker-free group, so it
//! measures registration, motion and the noise model on every group for free
//! ([`witness`]).
// `!(x < limit)` is deliberate throughout: it also rejects NaN.
#![allow(clippy::neg_cmp_op_on_partial_ord)]
use rayon::prelude::*;

/// Per tile row: z^2 sums and counts per tile, PTC bins, witness-pair sums,
/// and each tile's witness-pair sums per class ([`LocalSums`]).
type WitnessRow = (
    Vec<f64>,
    Vec<u64>,
    Vec<[f64; 3]>,
    [[[f64; 5]; 2]; 4],
    Vec<[LocalSums; 2]>,
);

/// One tile's witness-pair sums for one class of sites, over the sites the
/// pair regression uses (gradient at least five times its noise):
/// `[gx^2, gx gy, gy^2, gx d, gy d, d^2, var(d), sites]`.
type LocalSums = [f64; 8];

/// Fewest regression sites a tile's class needs for [`Witness::tile_local_px`].
pub const LOCAL_MIN_SITES: f64 = 64.0;

/// One member's samples: the whole decoded buffer and its active window.
#[derive(Clone, Copy)]
pub struct MemberView<'a> {
    pub data: &'a [u16],
    pub stride: usize,
    pub buffer_height: usize,
    /// Active area origin and size in buffer coordinates.
    pub active: [usize; 4],
    pub black: f32,
    /// Raw white level. Samples within [`CLIP_FRACTION`] of it are treated as
    /// clipped: their value no longer follows the scene, so a pair with one
    /// clipped member says nothing about registration.
    pub white: f32,
}

/// Fraction of the black-to-white headroom above which a sample counts as
/// clipped for the witness (and for its gradient neighbours).
pub const CLIP_FRACTION: f32 = 0.95;

impl MemberView<'_> {
    /// Black-subtracted sample at active coordinates `(x, y)`, which may lie
    /// outside the active area (the margin) as long as it is inside the buffer.
    #[inline]
    fn at(&self, x: isize, y: isize) -> Option<f32> {
        let bx = self.active[0] as isize + x;
        let by = self.active[1] as isize + y;
        if bx < 0 || by < 0 || bx as usize >= self.stride || by as usize >= self.buffer_height {
            return None;
        }
        Some(f32::from(self.data[by as usize * self.stride + bx as usize]) - self.black)
    }

    /// [`Self::at`], or `None` when the sample is clipped.
    #[inline]
    fn unclipped(&self, x: isize, y: isize) -> Option<f32> {
        self.at(x, y)
            .filter(|v| *v < CLIP_FRACTION * (self.white - self.black))
    }
}

/// RGGB colour of active-coordinate photosite `(x, y)`: 0 red, 1 green, 2 blue.
#[inline]
pub fn cfa_colour(x: isize, y: isize) -> usize {
    match (x.rem_euclid(2), y.rem_euclid(2)) {
        (0, 0) => 0,
        (1, 1) => 2,
        _ => 1,
    }
}

/// A central region of interest in active coordinates, with a margin that
/// keeps every offset in the search window inside the buffer.
fn roi(m: &MemberView<'_>, fraction: f64) -> [usize; 4] {
    let (w, h) = (m.active[2], m.active[3]);
    let rw = ((w as f64 * fraction) as usize).max(64) & !1;
    let rh = ((h as f64 * fraction) as usize).max(64) & !1;
    [((w - rw) / 2) & !1, ((h - rh) / 2) & !1, rw, rh]
}

/// White balance from the data: per-colour multipliers making each colour's
/// mean over the central region equal green's, so that [`box2`] luma is close
/// to colour-blind on neutral and smooth scenes.
pub fn balance(m: &MemberView<'_>) -> [f32; 3] {
    let r = roi(m, 0.8);
    let mut sum = [0f64; 3];
    let mut n = [0u64; 3];
    for y in (r[1]..r[1] + r[3]).step_by(7) {
        for x in (r[0]..r[0] + r[2]).step_by(3) {
            let (x, y) = (x as isize, y as isize);
            if let Some(v) = m.at(x, y) {
                let c = cfa_colour(x, y);
                sum[c] += f64::from(v);
                n[c] += 1;
            }
        }
    }
    let mean = |c: usize| sum[c] / n[c].max(1) as f64;
    let g = mean(1);
    [0, 1, 2].map(|c| {
        let v = mean(c);
        if v > 1.0 && g > 1.0 {
            (g / v) as f32
        } else {
            1.0
        }
    })
}

/// Side of the block luma used for member registration. Any even-sided block
/// holds exactly a quarter red, half green and a quarter blue photosites
/// whatever its parity, so block sums are comparable across 1-photosite
/// shifts; 8 also averages the noise down eightfold.
const BLOCK: isize = 8;

/// Integral image of white-balanced samples over a rectangle of active
/// coordinates `[x0, x0 + w) x [y0, y0 + h)`, `(w + 1) x (h + 1)`, f64.
struct Integral {
    x0: isize,
    y0: isize,
    w: usize,
    sum: Vec<f64>,
}

impl Integral {
    fn new(m: &MemberView<'_>, bal: &[f32; 3], x0: isize, y0: isize, w: usize, h: usize) -> Self {
        let stride = w + 1;
        let mut sum = vec![0f64; stride * (h + 1)];
        // Row prefix sums in parallel, then a serial-free column pass per chunk.
        sum[stride..]
            .par_chunks_mut(stride)
            .enumerate()
            .for_each(|(y, row)| {
                let mut acc = 0f64;
                for x in 0..w {
                    let (ax, ay) = (x0 + x as isize, y0 + y as isize);
                    let v = m
                        .at(ax, ay)
                        .map_or(0.0, |s| f64::from(s * bal[cfa_colour(ax, ay)]));
                    acc += v;
                    row[x + 1] = acc;
                }
            });
        // Column pass: each column accumulates top to bottom, as a serial
        // `row[y] += row[y - 1]` sweep would, with blocks of columns in
        // parallel, in place: each element becomes its row prefix plus the
        // finished element above it, the same addition in the same order, so
        // the sums are bit-identical to the serial sweep (and to the strip
        // copies this pass used to go through, 2 x 120 MB per integral at
        // 61 MP).
        const COLUMNS: usize = 256;
        let rows = h + 1;
        struct Cells(*mut f64);
        // SAFETY: each task below writes only its own columns.
        unsafe impl Send for Cells {}
        unsafe impl Sync for Cells {}
        let cells = Cells(sum.as_mut_ptr());
        let cells = &cells;
        (0..stride.div_ceil(COLUMNS)).into_par_iter().for_each(|b| {
            let (xa, xb) = (b * COLUMNS, ((b + 1) * COLUMNS).min(stride));
            for y in 1..rows {
                // SAFETY: rows `y - 1` and `y` lie in `sum`; block `b`
                // alone reads and writes columns `xa..xb`, and reads row
                // `y - 1` only after writing it.
                unsafe {
                    let above = cells.0.add((y - 1) * stride);
                    let here = cells.0.add(y * stride);
                    for x in xa..xb {
                        *here.add(x) = *here.add(x) + *above.add(x);
                    }
                }
            }
        });
        Self { x0, y0, w, sum }
    }
    /// Sum of the `BLOCK x BLOCK` block whose top-left is active `(x, y)`.
    #[inline]
    fn block(&self, x: isize, y: isize) -> f64 {
        let s = self.w + 1;
        let (x, y) = ((x - self.x0) as usize, (y - self.y0) as usize);
        let b = BLOCK as usize;
        self.sum[(y + b) * s + x + b] - self.sum[y * s + x + b] - self.sum[(y + b) * s + x]
            + self.sum[y * s + x]
    }
}

/// Registration of one member against member 1 on block luma.
#[derive(Clone, Copy, Debug)]
pub struct Fit {
    /// Integer offset (see the module's convention).
    pub offset: (isize, isize),
    /// True offset minus `offset`, corrected for gradient-noise attenuation.
    pub residual: [f64; 2],
    /// Attenuation factor of the least-squares slope on the weaker axis:
    /// structure gradient energy over observed gradient energy. Near 1 means
    /// the scene dominates its noise; near 0 means no usable structure (a
    /// dark frame), and the offset is not measured.
    pub structure: f64,
    /// Member flux over member 1's (exposure gain).
    pub gain: f64,
}

struct Normal {
    a: [f64; 9],
}

fn normal(r: &Integral, k: &Integral, o: (isize, isize), roi: [isize; 4], step: usize) -> Normal {
    let rows: Vec<[f64; 9]> = (roi[1]..roi[1] + roi[3])
        .step_by(step)
        .collect::<Vec<_>>()
        .par_iter()
        .map(|&y| {
            let mut acc = [0f64; 9];
            for x in (roi[0]..roi[0] + roi[2]).step_by(step) {
                let c = r.block(x, y);
                let gx = 0.5 * (r.block(x + 1, y) - r.block(x - 1, y));
                let gy = 0.5 * (r.block(x, y + 1) - r.block(x, y - 1));
                let kk = k.block(x + o.0, y + o.1);
                let e = kk - c;
                acc[0] += gx * gx;
                acc[1] += gx * gy;
                acc[2] += gy * gy;
                acc[3] += gx * e;
                acc[4] += gy * e;
                acc[5] += kk;
                acc[6] += c;
                acc[7] += e * e;
                acc[8] += 1.0;
            }
            acc
        })
        .collect();
    let mut a = [0f64; 9];
    for row in rows {
        for (t, v) in a.iter_mut().zip(row) {
            *t += v;
        }
    }
    Normal { a }
}

/// Register `member` against `reference`: iterated Lucas-Kanade on block
/// luma from `(0, 0)`, moving the integer read position until the remainder
/// rounds to zero (at most `search` photosites each way), then the remainder
/// corrected for the attenuation that noise in the reference gradient causes.
pub fn register(
    reference: &MemberView<'_>,
    member: &MemberView<'_>,
    search: isize,
    step: usize,
) -> Fit {
    Reference::new(reference, search).register(member, step)
}

/// The reference side of [`register`], built once for any number of
/// members: the white balance and block-luma integral depend on the
/// reference and the search radius only.
pub struct Reference {
    bal: [f32; 3],
    roi: [isize; 4],
    search: isize,
    window: (isize, isize, usize, usize),
    integral: Integral,
}

impl Reference {
    pub fn new(reference: &MemberView<'_>, search: isize) -> Self {
        let bal = balance(reference);
        let (w, h) = (reference.active[2] as isize, reference.active[3] as isize);
        // Central half of the frame; integrals extend by the search and block.
        let roi = [w / 4, h / 4, w / 2, h / 2];
        let pad = search + 2;
        let (x0, y0) = (roi[0] - pad, roi[1] - pad);
        let (iw, ih) = (
            (roi[2] + 2 * pad + BLOCK) as usize,
            (roi[3] + 2 * pad + BLOCK) as usize,
        );
        let integral = Integral::new(reference, &bal, x0, y0, iw, ih);
        Self {
            bal,
            roi,
            search,
            window: (x0, y0, iw, ih),
            integral,
        }
    }

    /// [`register`] `member` against this reference.
    pub fn register(&self, member: &MemberView<'_>, step: usize) -> Fit {
        let (x0, y0, iw, ih) = self.window;
        let k = Integral::new(member, &self.bal, x0, y0, iw, ih);
        fit_member(&self.integral, &k, self.roi, self.search, step)
    }
}

fn fit_member(r: &Integral, k: &Integral, roi: [isize; 4], search: isize, step: usize) -> Fit {
    let mut o = (0isize, 0isize);
    let unmeasured = Fit {
        offset: o,
        residual: [f64::NAN; 2],
        structure: 0.0,
        gain: 1.0,
    };
    // Raw Gauss-Newton steps move the integer read position; the remainder is
    // judged only once the position has converged, because before that the
    // residual still holds the unexplained shift.
    let mut a = normal(r, k, o, roi, step).a;
    for _ in 0..6 {
        let det = a[0] * a[2] - a[1] * a[1];
        if !(det > 0.0) || a[8] < 16.0 {
            return unmeasured;
        }
        let d = [
            (a[2] * a[3] - a[1] * a[4]) / det,
            (a[0] * a[4] - a[1] * a[3]) / det,
        ];
        let next = (
            (o.0 as f64 - d[0])
                .round()
                .clamp(-search as f64, search as f64) as isize,
            (o.1 as f64 - d[1])
                .round()
                .clamp(-search as f64, search as f64) as isize,
        );
        if next == o {
            break;
        }
        o = next;
        a = normal(r, k, o, roi, step).a;
    }
    let det = a[0] * a[2] - a[1] * a[1];
    if !(det > 0.0) || a[8] < 16.0 {
        return unmeasured;
    }
    let d = [
        (a[2] * a[3] - a[1] * a[4]) / det,
        (a[0] * a[4] - a[1] * a[3]) / det,
    ];
    // Residual variance after the fit is about twice one block's noise; a
    // central difference of overlapping blocks carries 1/(2 BLOCK) of a
    // block's noise variance per axis.
    let var_e = ((a[7] - (d[0] * a[3] + d[1] * a[4])) / (a[8] - 2.0)).max(0.0);
    let grad_noise = var_e / (4.0 * BLOCK as f64);
    let lx = 1.0 - grad_noise / (a[0] / a[8]).max(f64::MIN_POSITIVE);
    let ly = 1.0 - grad_noise / (a[2] / a[8]).max(f64::MIN_POSITIVE);
    Fit {
        offset: o,
        residual: [-d[0] / lx.max(0.05), -d[1] / ly.max(0.05)],
        structure: lx.min(ly).clamp(0.0, 1.0),
        gain: a[5] / a[6].max(f64::MIN_POSITIVE),
    }
}

/// Whether integer offsets cover all four CFA parities (each site then gets
/// red once, blue once, green twice).
pub fn covers_all_parities(offsets: &[(isize, isize)]) -> bool {
    let mut seen = [false; 4];
    for &(x, y) in offsets {
        seen[(x.rem_euclid(2) + 2 * y.rem_euclid(2)) as usize] = true;
    }
    offsets.len() == 4 && seen.iter().all(|s| *s)
}

/// For site `(x, y)`, the member delivering each colour: `[red, green_a,
/// green_b, blue]`, members ordered by index for the greens.
pub fn site_members(offsets: &[(isize, isize); 4], x: isize, y: isize) -> [usize; 4] {
    let mut out = [usize::MAX; 4];
    let mut green = 0;
    for (k, o) in offsets.iter().enumerate() {
        match cfa_colour(x + o.0, y + o.1) {
            0 => out[0] = k,
            2 => out[3] = k,
            _ => {
                out[1 + green.min(1)] = k;
                green += 1;
            }
        }
    }
    out
}

/// Green-witness statistics of one group.
#[derive(Clone, Debug, Default)]
pub struct Witness {
    /// Tile size in sites and tile grid.
    pub tile: usize,
    pub tiles: [usize; 2],
    /// Mean of `z^2` per tile, row-major.
    pub tile_z2: Vec<f32>,
    /// Photon-transfer bins on low-gradient sites: (mean signal DN, half the
    /// variance of the gain-corrected green difference, count), signal bins of
    /// equal width in log signal.
    pub ptc: Vec<(f64, f64, u64)>,
    /// Whole-group mean `z^2` over every site.
    pub mean_z2: f64,
    /// Sub-photosite misregistration of each witness pair, `[x+y even, odd]`
    /// sites: the least-squares `e` in `G_a - G_b = grad G . e` over sites
    /// whose green gradient is at least five times its noise. `e` is member
    /// b's displacement relative to member a (members as in `pair_members`).
    /// Colour-exact: both samples are green, at the same site, unresampled.
    pub pair_shift: [[f64; 2]; 2],
    pub pair_members: [[usize; 2]; 2],
    /// The same regression per image quadrant (`[top-left, top-right,
    /// bottom-left, bottom-right]`). Estimator noise shows as quadrants that
    /// disagree at random; a translation as agreement; a rotation or a
    /// field-dependent effect as a pattern.
    pub pair_shift_quadrants: [[[f64; 2]; 2]; 4],
    /// Per tile (row-major, as `tile_z2`): the disagreement left once each
    /// witness pair's whole-group shift (`pair_shift`) is taken out, as the
    /// displacement in photosites that would cause it, the larger of the two
    /// classes; `NaN` where neither class has [`LOCAL_MIN_SITES`] regression
    /// sites.
    ///
    /// For a class with sums `A` (gradient outer products), `b` (gradient
    /// times difference), `D` (squared differences) and `V` (their injected
    /// noise variance) over its regression sites, and whole-group shift `e`,
    /// the leftover is `R = D - 2 e.b + e'Ae` and the value is
    /// `sqrt(max(0, R - V) / (tr A / 2))`: a local translation `u` of
    /// isotropic structure reads `|u|`. Unlike `tile_z2`, it does not grow
    /// with exposure: signal, gradient energy and the leftover scale
    /// together, and the noise is subtracted, not divided by.
    pub tile_local_px: Vec<f32>,
}

/// Measure the green witness. `gains[k]` is member `k`'s exposure relative to
/// member 1 (from [`register`]); samples are divided by it before
/// comparison. `variance(signal_dn)` is the injected per-sample noise variance
/// of one green photosite at that black-subtracted signal; `z` uses it, so a
/// wrong model shows as a global `mean_z2` away from 1, while motion and
/// misregistration show as tiles above the rest.
pub fn witness(
    members: &[MemberView<'_>; 4],
    offsets: &[(isize, isize); 4],
    gains: &[f64; 4],
    variance: impl Fn(f32) -> f32 + Sync,
    tile: usize,
) -> Witness {
    witness_impl::<true>(members, offsets, gains, variance, tile)
}

/// [`witness`] without the photon-transfer bins ([`Witness::ptc`] empty),
/// for a caller that does not read them (the group check): every other
/// field is the same, from the same sums in the same order.
pub fn witness_without_ptc(
    members: &[MemberView<'_>; 4],
    offsets: &[(isize, isize); 4],
    gains: &[f64; 4],
    variance: impl Fn(f32) -> f32 + Sync,
    tile: usize,
) -> Witness {
    witness_impl::<false>(members, offsets, gains, variance, tile)
}

fn witness_impl<const PTC: bool>(
    members: &[MemberView<'_>; 4],
    offsets: &[(isize, isize); 4],
    gains: &[f64; 4],
    variance: impl Fn(f32) -> f32 + Sync,
    tile: usize,
) -> Witness {
    if !covers_all_parities(offsets) {
        return Witness {
            tile,
            mean_z2: f64::NAN,
            ..Default::default()
        };
    }
    let (w, h) = (members[0].active[2], members[0].active[3]);
    let tiles = [w.div_ceil(tile), h.div_ceil(tile)];
    const BINS: usize = 48;
    let edges = |s: f64| ((s.max(1.0).ln() / (16384f64).ln()) * BINS as f64) as usize;
    let inv: [f32; 4] = gains.map(|g| (1.0 / g) as f32);
    // `site_members` depends on the site's parity only.
    let table: [[usize; 4]; 4] =
        std::array::from_fn(|p| site_members(offsets, (p & 1) as isize, (p >> 1) as isize));
    // Per tile row: z^2 sums per tile, PTC sums. Without the bins, each row's
    // site terms in one pass and the sums after it (`witness_row_terms`).
    if !PTC {
        let rows: Vec<WitnessRow> = (0..tiles[1])
            .into_par_iter()
            .map(|ty| witness_row_terms(members, offsets, &inv, &table, &variance, tile, ty))
            .collect();
        return witness_finish(rows, offsets, tile, tiles);
    }
    let rows: Vec<WitnessRow> = (0..tiles[1])
        .into_par_iter()
        .map(|ty| {
            let mut z2 = vec![0f64; tiles[0]];
            let mut n = vec![0u64; tiles[0]];
            let mut ptc = vec![[0f64; 3]; BINS + 1];
            let mut pair = [[[0f64; 5]; 2]; 4];
            let mut local = vec![[[0f64; 8]; 2]; tiles[0]];
            for y in ty * tile..((ty + 1) * tile).min(h) {
                for x in 0..w {
                    let (x, y) = (x as isize, y as isize);
                    let sm = table[((x & 1) | ((y & 1) << 1)) as usize];
                    let (a, b) = (sm[1], sm[2]);
                    let (Some(ga), Some(gb)) = (
                        members[a].unclipped(x + offsets[a].0, y + offsets[a].1),
                        members[b].unclipped(x + offsets[b].0, y + offsets[b].1),
                    ) else {
                        continue;
                    };
                    let (ga, gb) = (ga * inv[a], gb * inv[b]);
                    let s = 0.5 * (ga + gb);
                    let vs = variance(s);
                    let var = vs * (inv[a] * inv[a] + inv[b] * inv[b]);
                    let d = f64::from(ga - gb);
                    if var > 0.0 {
                        let t = x as usize / tile;
                        z2[t] += d * d / f64::from(var);
                        n[t] += 1;
                    }
                    // Low-gradient test on member a's own green neighbours
                    // (diagonals are green too): the difference of the two
                    // diagonal pairs must be within noise.
                    let o = offsets[a];
                    if let (Some(p), Some(q), Some(r), Some(u)) = (
                        members[a].unclipped(x + o.0 - 1, y + o.1 - 1),
                        members[a].unclipped(x + o.0 + 1, y + o.1 + 1),
                        members[a].unclipped(x + o.0 + 1, y + o.1 - 1),
                        members[a].unclipped(x + o.0 - 1, y + o.1 + 1),
                    ) {
                        let (d1, d2) = (f64::from((q - p) * inv[a]), f64::from((r - u) * inv[a]));
                        let (gx, gy) = (0.25 * (d1 + d2), 0.25 * (d1 - d2));
                        if gx * gx + gy * gy > 25.0 * f64::from(vs) {
                            let quadrant = usize::from(x as usize >= w / 2)
                                + 2 * usize::from(y as usize >= h / 2);
                            let acc = &mut pair[quadrant][((x + y) & 1) as usize];
                            acc[0] += gx * gx;
                            acc[1] += gx * gy;
                            acc[2] += gy * gy;
                            acc[3] += gx * d;
                            acc[4] += gy * d;
                            let l = &mut local[x as usize / tile][((x + y) & 1) as usize];
                            l[0] += gx * gx;
                            l[1] += gx * gy;
                            l[2] += gy * gy;
                            l[3] += gx * d;
                            l[4] += gy * d;
                            l[5] += d * d;
                            l[6] += f64::from(var);
                            l[7] += 1.0;
                        }
                        let grad = (p - q).abs().max((r - u).abs());
                        if PTC && grad * grad < 4.0 * vs && s > 0.0 {
                            let bin = edges(f64::from(s)).min(BINS);
                            ptc[bin][0] += f64::from(s);
                            ptc[bin][1] += d * d;
                            ptc[bin][2] += 1.0;
                        }
                    }
                }
            }
            (z2, n, ptc, pair, local)
        })
        .collect();
    witness_finish(rows, offsets, tile, tiles)
}

/// One tile row of [`witness_without_ptc`]: per row of sites, every site's
/// terms in one pass (inside the buffer straight from the rows, without the
/// per-sample bounds and `Option`s; at the edges as [`witness`] reads
/// them), then the sums in site order. The same terms, from the same
/// expressions, added in the same order as [`witness`]'s loop: the same bits
/// (`the_witness_without_bins_is_the_witness`). MEASURED on two A7CR scarab
/// groups on one thread: 588 ms to 400 ms (2026-11-18).
#[allow(clippy::too_many_arguments)]
fn witness_row_terms(
    members: &[MemberView<'_>; 4],
    offsets: &[(isize, isize); 4],
    inv: &[f32; 4],
    table: &[[usize; 4]; 4],
    variance: &(impl Fn(f32) -> f32 + Sync),
    tile: usize,
    ty: usize,
) -> WitnessRow {
    const BINS: usize = 48;
    fn row<'a>(m: &MemberView<'a>, yy: isize) -> Option<&'a [u16]> {
        let by = m.active[1] as isize + yy;
        (by >= 0 && (by as usize) < m.buffer_height)
            .then(|| &m.data[by as usize * m.stride..(by as usize + 1) * m.stride])
    }
    let (w, h) = (members[0].active[2], members[0].active[3]);
    let tiles_x = w.div_ceil(tile);
    let mut z2 = vec![0f64; tiles_x];
    let mut n = vec![0u64; tiles_x];
    let mut pair = [[[0f64; 5]; 2]; 4];
    // One row's site terms.
    let mut zt = vec![0f64; w];
    let mut zok = vec![false; w];
    let mut pt = vec![[0f64; 5]; w];
    let mut pv = vec![[0f64; 2]; w];
    let mut pok = vec![false; w];
    let mut local = vec![[[0f64; 8]; 2]; tiles_x];
    for y in ty * tile..((ty + 1) * tile).min(h) {
        let yi = y as isize;
        for px in 0..2usize {
            let sm = table[px | ((y & 1) << 1)];
            let (a, b) = (sm[1], sm[2]);
            let (ma, mb) = (&members[a], &members[b]);
            let (oa, ob) = (offsets[a], offsets[b]);
            let (ia, ib) = (inv[a], inv[b]);
            let ivar = ia * ia + ib * ib;
            let (clip_a, clip_b) = (
                CLIP_FRACTION * (ma.white - ma.black),
                CLIP_FRACTION * (mb.white - mb.black),
            );
            // Member a's rows y - 1, y, y + 1 about its offset; member b's.
            let rows = (
                row(ma, yi + oa.1),
                row(ma, yi + oa.1 - 1),
                row(ma, yi + oa.1 + 1),
                row(mb, yi + ob.1),
            );
            // Columns where every read of this parity is inside the buffer.
            let xa0 = ma.active[0] as isize + oa.0;
            let xb0 = mb.active[0] as isize + ob.0;
            let lo = (1 - xa0).max(-xb0).max(0) as usize;
            let hi = (ma.stride as isize - 1 - xa0)
                .min(mb.stride as isize - xb0)
                .clamp(0, w as isize) as usize;
            let mut x = px;
            while x < w {
                let xi = x as isize;
                let read = match rows {
                    (Some(ra), Some(ru), Some(rd), Some(rb)) if x >= lo && x < hi => {
                        let ka = (xa0 + xi) as usize;
                        let kb = (xb0 + xi) as usize;
                        let ga = f32::from(ra[ka]) - ma.black;
                        let gb = f32::from(rb[kb]) - mb.black;
                        let p = f32::from(ru[ka - 1]) - ma.black;
                        let q = f32::from(rd[ka + 1]) - ma.black;
                        let r = f32::from(ru[ka + 1]) - ma.black;
                        let u = f32::from(rd[ka - 1]) - ma.black;
                        (
                            (ga < clip_a).then_some(ga),
                            (gb < clip_b).then_some(gb),
                            (p < clip_a && q < clip_a && r < clip_a && u < clip_a)
                                .then_some((p, q, r, u)),
                        )
                    }
                    _ => (
                        ma.unclipped(xi + oa.0, yi + oa.1),
                        mb.unclipped(xi + ob.0, yi + ob.1),
                        match (
                            ma.unclipped(xi + oa.0 - 1, yi + oa.1 - 1),
                            ma.unclipped(xi + oa.0 + 1, yi + oa.1 + 1),
                            ma.unclipped(xi + oa.0 + 1, yi + oa.1 - 1),
                            ma.unclipped(xi + oa.0 - 1, yi + oa.1 + 1),
                        ) {
                            (Some(p), Some(q), Some(r), Some(u)) => Some((p, q, r, u)),
                            _ => None,
                        },
                    ),
                };
                zok[x] = false;
                pok[x] = false;
                if let (Some(ga), Some(gb), neighbours) = read {
                    let (ga, gb) = (ga * ia, gb * ib);
                    let s = 0.5 * (ga + gb);
                    let vs = variance(s);
                    let var = vs * ivar;
                    let d = f64::from(ga - gb);
                    if var > 0.0 {
                        zt[x] = d * d / f64::from(var);
                        zok[x] = true;
                    }
                    if let Some((p, q, r, u)) = neighbours {
                        let (d1, d2) = (f64::from((q - p) * ia), f64::from((r - u) * ia));
                        let (gx, gy) = (0.25 * (d1 + d2), 0.25 * (d1 - d2));
                        if gx * gx + gy * gy > 25.0 * f64::from(vs) {
                            pt[x] = [gx * gx, gx * gy, gy * gy, gx * d, gy * d];
                            pv[x] = [d * d, f64::from(var)];
                            pok[x] = true;
                        }
                    }
                }
                x += 2;
            }
        }
        // The sums, in site order.
        let qy = 2 * usize::from(y >= h / 2);
        for x in 0..w {
            if zok[x] {
                let t = x / tile;
                z2[t] += zt[x];
                n[t] += 1;
            }
            if pok[x] {
                let acc = &mut pair[usize::from(x >= w / 2) + qy][(x + y) & 1];
                let v = &pt[x];
                acc[0] += v[0];
                acc[1] += v[1];
                acc[2] += v[2];
                acc[3] += v[3];
                acc[4] += v[4];
                let l = &mut local[x / tile][(x + y) & 1];
                l[0] += v[0];
                l[1] += v[1];
                l[2] += v[2];
                l[3] += v[3];
                l[4] += v[4];
                l[5] += pv[x][0];
                l[6] += pv[x][1];
                l[7] += 1.0;
            }
        }
    }
    (z2, n, vec![[0f64; 3]; BINS + 1], pair, local)
}

/// [`witness`]'s reduction of its tile rows, in row order.
fn witness_finish(
    rows: Vec<WitnessRow>,
    offsets: &[(isize, isize); 4],
    tile: usize,
    tiles: [usize; 2],
) -> Witness {
    const BINS: usize = 48;
    let mut out = Witness {
        tile,
        tiles,
        ..Default::default()
    };
    let mut ptc = vec![[0f64; 3]; BINS + 1];
    let mut pair = [[[0f64; 5]; 2]; 4];
    let (mut total, mut count) = (0f64, 0u64);
    let mut local: Vec<[LocalSums; 2]> = Vec::with_capacity(tiles[0] * tiles[1]);
    for (z2, n, p, q, l) in rows {
        local.extend(l);
        for (quadrant, v) in pair.iter_mut().zip(q) {
            for (acc, v) in quadrant.iter_mut().zip(v) {
                for (t, x) in acc.iter_mut().zip(v) {
                    *t += x;
                }
            }
        }
        for (s, c) in z2.iter().zip(&n) {
            out.tile_z2.push(if *c > 0 {
                (*s / *c as f64) as f32
            } else {
                f32::NAN
            });
            total += s;
            count += c;
        }
        for (acc, v) in ptc.iter_mut().zip(p) {
            acc[0] += v[0];
            acc[1] += v[1];
            acc[2] += v[2];
        }
    }
    out.mean_z2 = total / count.max(1) as f64;
    let solve = |a: &[f64; 5]| {
        let det = a[0] * a[2] - a[1] * a[1];
        if det > 0.0 {
            [
                (a[2] * a[3] - a[1] * a[4]) / det,
                (a[0] * a[4] - a[1] * a[3]) / det,
            ]
        } else {
            [f64::NAN; 2]
        }
    };
    for class in 0..2 {
        let mut whole = [0f64; 5];
        for (q, quadrant) in pair.iter().enumerate() {
            out.pair_shift_quadrants[q][class] = solve(&quadrant[class]);
            for (t, x) in whole.iter_mut().zip(quadrant[class]) {
                *t += x;
            }
        }
        out.pair_shift[class] = solve(&whole);
        let sm = site_members(offsets, class as isize, 0);
        out.pair_members[class] = [sm[1], sm[2]];
    }
    out.tile_local_px = local
        .iter()
        .map(|t| {
            let px = |class: usize| local_displacement(&t[class], out.pair_shift[class]);
            match (px(0), px(1)) {
                (Some(a), Some(b)) => a.max(b) as f32,
                (Some(a), None) | (None, Some(a)) => a as f32,
                (None, None) => f32::NAN,
            }
        })
        .collect();
    out.ptc = ptc
        .into_iter()
        .filter(|v| v[2] >= 64.0)
        .map(|v| (v[0] / v[2], v[1] / v[2] / 2.0, v[2] as u64))
        .collect();
    out
}

/// One tile class's leftover disagreement as a displacement in photosites
/// (see [`Witness::tile_local_px`]), or `None` with too few regression sites
/// or no whole-group shift to take out.
fn local_displacement(s: &LocalSums, e: [f64; 2]) -> Option<f64> {
    let structure = 0.5 * (s[0] + s[2]);
    if !(s[7] >= LOCAL_MIN_SITES) || !(structure > 0.0) || !e.iter().all(|v| v.is_finite()) {
        return None;
    }
    let leftover = s[5] - 2.0 * (e[0] * s[3] + e[1] * s[4])
        + e[0] * e[0] * s[0]
        + 2.0 * e[0] * e[1] * s[1]
        + e[1] * e[1] * s[2];
    Some(((leftover - s[6]).max(0.0) / structure).sqrt())
}

/// Weighted least-squares fit of `variance = read^2 + gain * signal` to
/// photon-transfer bins (weights: count / predicted variance^2, iterated).
/// Returns `(gain DN per e-, read noise DN)`.
pub fn fit_photon_transfer(bins: &[(f64, f64, u64)]) -> Option<(f64, f64)> {
    if bins.len() < 3 {
        return None;
    }
    let (mut g, mut r2) = (1.0f64, 1.0f64);
    for _ in 0..8 {
        let (mut sw, mut sx, mut sy, mut sxx, mut sxy) = (0f64, 0f64, 0f64, 0f64, 0f64);
        for &(s, v, n) in bins {
            let pred = (r2 + g * s).max(1e-6);
            let w = n as f64 / (pred * pred);
            sw += w;
            sx += w * s;
            sy += w * v;
            sxx += w * s * s;
            sxy += w * s * v;
        }
        let det = sw * sxx - sx * sx;
        if det <= 0.0 {
            return None;
        }
        g = (sw * sxy - sx * sy) / det;
        r2 = (sy - g * sx) / sw;
    }
    (g.is_finite() && r2.is_finite()).then(|| (g, r2.max(0.0).sqrt()))
}

/// Assemble a group into three measured, black-subtracted full-resolution
/// planes `[red, green, blue]` over member 1's active area, row-major
/// `width x height`. Member `k`'s samples are multiplied by `colour_gain[c]`
/// (white balance, as the merge's mosaic applies) and divided by its exposure
/// gain. Green is the mean of the two green samples. A site whose shifted
/// photosite falls outside a member's buffer is `NaN` (never a guess).
pub fn assemble(
    members: &[MemberView<'_>; 4],
    offsets: &[(isize, isize); 4],
    gains: &[f64; 4],
    colour_gain: [f32; 3],
) -> [Vec<f32>; 3] {
    assert!(
        covers_all_parities(offsets),
        "assemble needs offsets covering all four CFA parities; demote the group instead"
    );
    let (w, h) = (members[0].active[2], members[0].active[3]);
    let inv: [f32; 4] = gains.map(|g| (1.0 / g) as f32);
    let mut planes = [vec![0f32; w * h], vec![0f32; w * h], vec![0f32; w * h]];
    let [r, g, b] = &mut planes;
    r.par_chunks_mut(w)
        .zip(g.par_chunks_mut(w))
        .zip(b.par_chunks_mut(w))
        .enumerate()
        .for_each(|(y, ((rr, gg), bb))| {
            let y = y as isize;
            for x in 0..w {
                let xi = x as isize;
                let sm = site_members(offsets, xi, y);
                let get = |k: usize| {
                    members[k]
                        .at(xi + offsets[k].0, y + offsets[k].1)
                        .map_or(f32::NAN, |v| v * inv[k])
                };
                rr[x] = get(sm[0]) * colour_gain[0];
                gg[x] = (get(sm[1]) + get(sm[2])) * 0.5 * colour_gain[1];
                bb[x] = get(sm[3]) * colour_gain[2];
            }
        });
    planes
}

/// First-order compensation of the members' measured sub-photosite
/// displacement, on assembled channel rows.
///
/// [`register`]'s `residual` is member `k`'s true offset minus its integer
/// one: reading member `k` at the integer position sees the scene at member
/// 1's `x - r_k`, so a sample is `S(x - r_k) ~ S(x) - r_k . grad S`, and
/// adding `r_k . grad C` (the assembled channel's own central-difference
/// gradient) puts it back at `x` to first order. Green, the mean of two
/// members, takes the mean of their residuals.
///
/// `raw` holds `rows + 2` assembled rows of `w` RGB triples: the output rows
/// with one row above and below (the caller clamps those at the frame's
/// edges). `y0` is the active-area row of the first output row (its CFA
/// parity selects the members). `sign` is `1` to compensate; `-1` is the
/// placebo that doubles the error instead.
#[allow(clippy::too_many_arguments)]
pub fn compensate_rows(
    raw: &[[f32; 3]],
    w: usize,
    rows: usize,
    y0: isize,
    offsets: &[(isize, isize); 4],
    residuals: &[[f64; 2]; 4],
    sign: f32,
    out: [&mut [f32]; 3],
) {
    compensate_rows_cols(raw, w, rows, y0, offsets, residuals, sign, out, 0..w);
}

/// [`compensate_rows`] of the columns `xs` only: the same value at each of
/// them (every output reads its own column and the clamped columns either
/// side, the clamp at the row's own ends). `raw` needs valid triples only at
/// columns `xs.start - 1 ..= xs.end` (within the row); outputs outside `xs`
/// are left as they are.
#[allow(clippy::too_many_arguments)]
pub fn compensate_rows_cols(
    raw: &[[f32; 3]],
    w: usize,
    rows: usize,
    y0: isize,
    offsets: &[(isize, isize); 4],
    residuals: &[[f64; 2]; 4],
    sign: f32,
    out: [&mut [f32]; 3],
    xs: std::ops::Range<usize>,
) {
    assert_eq!(raw.len(), (rows + 2) * w);
    assert!(xs.end <= w, "columns past the row");
    let [r, g, b] = out;
    let res: [[f32; 2]; 4] = residuals.map(|v| [sign * v[0] as f32, sign * v[1] as f32]);
    for k in 0..rows {
        let y = y0 + k as isize;
        let (up, mid, down) = (k * w, (k + 1) * w, (k + 2) * w);
        for x in xs.clone() {
            let (xm, xp) = (x.saturating_sub(1), (x + 1).min(w - 1));
            let span = (xp - xm).max(1) as f32;
            let grad = |c: usize| {
                [
                    (raw[mid + xp][c] - raw[mid + xm][c]) / span,
                    0.5 * (raw[down + x][c] - raw[up + x][c]),
                ]
            };
            let dot = |d: [f32; 2], gr: [f32; 2]| d[0] * gr[0] + d[1] * gr[1];
            let sm = site_members(offsets, x as isize, y);
            let v = raw[mid + x];
            let i = k * w + x;
            r[i] = v[0] + dot(res[sm[0]], grad(0));
            let dg = [
                0.5 * (res[sm[1]][0] + res[sm[2]][0]),
                0.5 * (res[sm[1]][1] + res[sm[2]][1]),
            ];
            g[i] = v[1] + dot(dg, grad(1));
            b[i] = v[2] + dot(res[sm[3]], grad(2));
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Every column window of `compensate_rows_cols`, given valid triples
    /// only at the window and one column either side, writes exactly what
    /// the whole-row `compensate_rows` writes there and nothing elsewhere,
    /// at the row's ends included.
    #[test]
    fn compensated_columns_equal_the_whole_row() {
        let (w, rows) = (37usize, 5usize);
        let mut seed = 0x1234_5678_9ABC_DEF0u64;
        let mut next = || {
            seed ^= seed << 13;
            seed ^= seed >> 7;
            seed ^= seed << 17;
            ((seed >> 40) as f32 / (1u64 << 24) as f32 - 0.5) * 4000.0
        };
        let raw: Vec<[f32; 3]> = (0..(rows + 2) * w)
            .map(|_| [next(), next(), next()])
            .collect();
        let offsets = [(0, 0), (1, 0), (1, 1), (0, 1)];
        let residuals = [[0.0, 0.0], [0.13, -0.07], [-0.21, 0.05], [0.04, 0.3]];
        let mut want = [
            vec![0f32; rows * w],
            vec![0f32; rows * w],
            vec![0f32; rows * w],
        ];
        {
            let [r, g, b] = &mut want;
            compensate_rows(&raw, w, rows, 3, &offsets, &residuals, 1.0, [r, g, b]);
        }
        for (a, b) in [
            (0usize, 1usize),
            (0, 5),
            (3, 9),
            (10, 37),
            (36, 37),
            (0, 37),
        ] {
            // Only the window and its neighbours hold the real triples.
            let mut partial = vec![[f32::NAN; 3]; raw.len()];
            for e in 0..rows + 2 {
                for x in a.saturating_sub(1)..(b + 1).min(w) {
                    partial[e * w + x] = raw[e * w + x];
                }
            }
            let mut got = [
                vec![-7.0f32; rows * w],
                vec![-7.0f32; rows * w],
                vec![-7.0f32; rows * w],
            ];
            {
                let [r, g, bb] = &mut got;
                compensate_rows_cols(
                    &partial,
                    w,
                    rows,
                    3,
                    &offsets,
                    &residuals,
                    1.0,
                    [r, g, bb],
                    a..b,
                );
            }
            for c in 0..3 {
                for k in 0..rows {
                    for x in 0..w {
                        let (v, u) = (got[c][k * w + x], want[c][k * w + x]);
                        if (a..b).contains(&x) {
                            assert_eq!(v.to_bits(), u.to_bits(), "{a}..{b} c{c} k{k} x{x}");
                        } else {
                            assert_eq!(v, -7.0, "{a}..{b} wrote outside its columns");
                        }
                    }
                }
            }
        }
    }

    /// A smooth-plus-texture scene sampled into four RGGB mosaics shifted by
    /// `shifts` photosites, in a buffer with a margin, with optional gains.
    fn group(shifts: [(isize, isize); 4], gains: [f32; 4]) -> (Vec<Vec<u16>>, [usize; 4]) {
        let (stride, bh) = (180usize, 140usize);
        let active = [8usize, 6, 160, 124];
        let scene = |c: usize, x: isize, y: isize| -> f32 {
            let (xf, yf) = (x as f32, y as f32);
            let base = 900.0 + 400.0 * ((xf * 0.21).sin() * (yf * 0.17).cos());
            let tex = 300.0 * (((x * 7 + y * 13) % 17) as f32 / 17.0);
            [1.0, 1.6, 0.8][c] * (base + tex)
        };
        let data = shifts
            .iter()
            .zip(gains)
            .map(|(s, gain)| {
                let mut d = vec![0u16; stride * bh];
                for by in 0..bh {
                    for bx in 0..stride {
                        // Member photosite (ax, ay) sees scene point (ax - s).
                        let (ax, ay) = (bx as isize - 8, by as isize - 6);
                        let c = cfa_colour(ax, ay);
                        d[by * stride + bx] =
                            (512.0 + gain * scene(c, ax - s.0, ay - s.1)).round() as u16;
                    }
                }
                d
            })
            .collect();
        (data, active)
    }
    fn views<'a>(data: &'a [Vec<u16>], active: [usize; 4]) -> [MemberView<'a>; 4] {
        std::array::from_fn(|k| MemberView {
            data: &data[k],
            stride: 180,
            buffer_height: 140,
            active,
            black: 512.0,
            white: 15360.0,
        })
    }

    /// `witness_without_ptc` (the per-row form) gives every field of
    /// `witness` but the bins, bit for bit: groups whose members are
    /// shifted out to the buffer's edge (the per-sample path) and back, with
    /// gains, clipped samples and tiles that do not divide the frame.
    #[test]
    fn the_witness_without_bins_is_the_witness() {
        for shifts in [
            [(0, 0), (1, 0), (1, 1), (0, 1)],
            [(0, 0), (0, -1), (1, -1), (1, 0)],
            [(0, 0), (-1, 0), (-1, -1), (0, -1)],
            [(0, 0), (1, 2), (-1, 1), (2, -3)],
        ] {
            let (mut data, mut active) = group(shifts, [1.0, 1.02, 0.97, 1.05]);
            // Clipped samples, and an active area reaching the buffer edge.
            for (k, d) in data.iter_mut().enumerate() {
                for i in (k * 37..d.len()).step_by(211) {
                    d[i] = 15300;
                }
            }
            for (active_x, tile) in [(8usize, 64usize), (0, 17), (19, 32)] {
                active[0] = active_x;
                active[2] = 180 - active_x.max(1) - 1;
                let v = views(&data, active);
                let offsets: [(isize, isize); 4] = shifts;
                if !covers_all_parities(&offsets) {
                    continue;
                }
                let gains = [1.0, 1.02, 0.97, 1.05];
                let variance = |s: f32| 0.37 * s.max(0.0) + 5.0;
                let full = witness(&v, &offsets, &gains, variance, tile);
                let part = witness_without_ptc(&v, &offsets, &gains, variance, tile);
                let bits = |x: &[f32]| x.iter().map(|v| v.to_bits()).collect::<Vec<_>>();
                assert_eq!(
                    bits(&full.tile_z2),
                    bits(&part.tile_z2),
                    "{shifts:?} {tile}"
                );
                assert_eq!(full.mean_z2.to_bits(), part.mean_z2.to_bits());
                assert_eq!(
                    format!("{:?}", full.pair_shift),
                    format!("{:?}", part.pair_shift)
                );
                assert_eq!(
                    format!("{:?}", full.pair_shift_quadrants),
                    format!("{:?}", part.pair_shift_quadrants)
                );
                assert_eq!(full.pair_members, part.pair_members);
                assert_eq!(
                    bits(&full.tile_local_px),
                    bits(&part.tile_local_px),
                    "{shifts:?} {tile}"
                );
                assert_eq!((full.tile, full.tiles), (part.tile, part.tiles));
                assert!(part.ptc.is_empty());
            }
        }
    }

    /// The strip-parallel column pass against the serial sweep it replaced,
    /// over several strips and a ragged last one, bit for bit.
    #[test]
    fn integral_column_pass_matches_the_serial_sweep() {
        let (stride, bh) = (1100usize, 37usize);
        let data: Vec<u16> = (0..stride * bh)
            .map(|i| (600 + (i * 7919 % 4093) + (i % 13) * 31) as u16)
            .collect();
        let view = MemberView {
            data: &data,
            stride,
            buffer_height: bh,
            active: [4, 2, 1090, 33],
            black: 512.0,
            white: 15360.0,
        };
        let bal = [1.37f32, 1.0, 0.71];
        let (x0, y0, w, h) = (-3isize, -1isize, 1093usize, 35usize);
        let got = Integral::new(&view, &bal, x0, y0, w, h);
        let s = w + 1;
        let mut want = vec![0f64; s * (h + 1)];
        for y in 0..h {
            let mut acc = 0f64;
            for x in 0..w {
                let (ax, ay) = (x0 + x as isize, y0 + y as isize);
                acc += view
                    .at(ax, ay)
                    .map_or(0.0, |v| f64::from(v * bal[cfa_colour(ax, ay)]));
                want[(y + 1) * s + x + 1] = acc;
            }
        }
        for y in 1..=h {
            for x in 0..s {
                want[y * s + x] += want[(y - 1) * s + x];
            }
        }
        assert_eq!(got.sum.len(), want.len());
        for (i, (a, b)) in got.sum.iter().zip(&want).enumerate() {
            assert_eq!(a.to_bits(), b.to_bits(), "element {i}");
        }
    }

    /// One reference for several members gives each member's [`register`].
    #[test]
    fn shared_reference_registers_like_register() {
        let shifts = [(0, 0), (1, 0), (1, 1), (0, 1)];
        let (data, active) = group(shifts, [1.0, 1.004, 0.997, 1.0]);
        let m = views(&data, active);
        let reference = Reference::new(&m[0], 2);
        for k in 1..4 {
            let a = register(&m[0], &m[k], 2, 1);
            let b = reference.register(&m[k], 1);
            assert_eq!(a.offset, b.offset);
            assert_eq!(a.gain.to_bits(), b.gain.to_bits());
            assert_eq!(a.structure.to_bits(), b.structure.to_bits());
            assert_eq!(a.residual.map(f64::to_bits), b.residual.map(f64::to_bits));
        }
    }

    #[test]
    fn offsets_parities_witness_and_assembly_recover_a_planted_group() {
        let shifts = [(0, 0), (1, 0), (1, 1), (0, 1)];
        let (data, active) = group(shifts, [1.0, 1.004, 0.997, 1.0]);
        let m = views(&data, active);
        let mut offsets = [(0isize, 0isize); 4];
        let mut gains = [1.0; 4];
        for k in 1..4 {
            let fit = register(&m[0], &m[k], 2, 1);
            assert_eq!(fit.offset, shifts[k], "member {k}");
            assert!(fit.structure > 0.8, "structure: {fit:?}");
            let d = fit.residual;
            assert!(d[0].abs() < 0.05 && d[1].abs() < 0.05, "{d:?}");
            offsets[k] = fit.offset;
            gains[k] = fit.gain;
        }
        assert!((gains[1] - 1.004).abs() < 2e-3 && (gains[2] - 0.997).abs() < 2e-3);
        assert!(covers_all_parities(&offsets));
        // Every site gets each colour from the right member.
        for (x, y) in [(0, 0), (1, 0), (0, 1), (5, 7)] {
            let sm = site_members(&offsets, x, y);
            assert_eq!(cfa_colour(x + offsets[sm[0]].0, y + offsets[sm[0]].1), 0);
            assert_eq!(cfa_colour(x + offsets[sm[3]].0, y + offsets[sm[3]].1), 2);
            assert_eq!(cfa_colour(x + offsets[sm[1]].0, y + offsets[sm[1]].1), 1);
            assert_eq!(cfa_colour(x + offsets[sm[2]].0, y + offsets[sm[2]].1), 1);
            assert_ne!(sm[1], sm[2]);
        }
        // Noise-free: assembled channels equal the scene (to rounding/gain).
        let planes = assemble(&m, &offsets, &gains, [1.0; 3]);
        let w = active[2];
        let (x, y) = (37usize, 41usize);
        let expect = |c: usize| {
            let (xf, yf) = (x as f32, y as f32);
            let base = 900.0 + 400.0 * ((xf * 0.21).sin() * (yf * 0.17).cos());
            let tex = 300.0 * ((((x * 7 + y * 13) % 17) as f32) / 17.0);
            [1.0, 1.6, 0.8][c] * (base + tex)
        };
        for (c, plane) in planes.iter().enumerate() {
            assert!((plane[y * w + x] - expect(c)).abs() < 3.0, "channel {c}");
        }
        // The witness: noise-free and registered, z^2 is ~0 under a unit model.
        let wit = witness(&m, &offsets, &gains, |_| 1.0, 32);
        assert!(wit.mean_z2 < 2.0, "{}", wit.mean_z2);
        for e in wit.pair_shift {
            assert!(
                e[0].abs() < 0.05 && e[1].abs() < 0.05,
                "{:?}",
                wit.pair_shift
            );
        }
    }

    #[test]
    fn failing_inputs_wrong_member_and_wrong_offset_are_detected() {
        let shifts = [(0, 0), (1, 0), (1, 1), (0, 1)];
        let (mut data, active) = group(shifts, [1.0; 4]);
        // Member 3 rolled by one extra photosite: integer search finds it, and
        // the parities then fail to cover the lattice.
        let (rolled, _) = group([(0, 0), (1, 0), (2, 1), (0, 1)], [1.0; 4]);
        data[2] = rolled[2].clone();
        let m = views(&data, active);
        let o = register(&m[0], &m[2], 2, 1).offset;
        assert_eq!(o, (2, 1));
        assert!(!covers_all_parities(&[(0, 0), (1, 0), o, (0, 1)]));
        // Forcing the nominal table on it lights the witness.
        let (good, _) = group(shifts, [1.0; 4]);
        let ok = views(&good, active);
        let nominal = [(0, 0), (1, 0), (1, 1), (0, 1)];
        let bad = witness(&m, &nominal, &[1.0; 4], |_| 1.0, 32).mean_z2;
        let fine = witness(&ok, &nominal, &[1.0; 4], |_| 1.0, 32).mean_z2;
        assert!(bad > 100.0 * fine.max(0.01), "bad {bad} fine {fine}");
    }

    #[test]
    fn clipped_samples_do_not_count_as_disagreement() {
        let shifts = [(0, 0), (1, 0), (1, 1), (0, 1)];
        let nominal = shifts;
        let (clean, active) = group(shifts, [1.0; 4]);
        let fine = witness(&views(&clean, active), &nominal, &[1.0; 4], |_| 1.0, 32).mean_z2;
        // A specular highlight that clips in one member only (as a few
        // hundredths of a photosite of motion does on a saturated peak).
        let mut data = clean.clone();
        for by in 40..60 {
            for bx in 60..80 {
                data[1][by * 180 + bx] = 16383;
            }
        }
        let m = views(&data, active);
        let clipped = witness(&m, &nominal, &[1.0; 4], |_| 1.0, 32).mean_z2;
        assert!(
            (clipped - fine).abs() <= 0.05 * fine.max(0.01) + 0.01,
            "clipped {clipped} fine {fine}"
        );
        // The same disturbance just below the clip threshold is disagreement.
        for by in 40..60 {
            for bx in 60..80 {
                data[1][by * 180 + bx] = 13000;
            }
        }
        let m = views(&data, active);
        let bright = witness(&m, &nominal, &[1.0; 4], |_| 1.0, 32).mean_z2;
        assert!(
            bright > 100.0 * fine.max(0.01),
            "bright {bright} fine {fine}"
        );
    }

    #[test]
    fn photon_transfer_fit_recovers_known_gain_and_read_noise() {
        let (g, r) = (0.42f64, 2.3f64);
        let bins: Vec<(f64, f64, u64)> = (1..30)
            .map(|i| {
                let s = (i * i * 12) as f64;
                (s, r * r + g * s, 1000)
            })
            .collect();
        let (fg, fr) = fit_photon_transfer(&bins).unwrap();
        assert!((fg - g).abs() < 1e-6 && (fr - r).abs() < 1e-6, "{fg} {fr}");
    }

    /// A smooth planted scene sampled by four members displaced by known
    /// sub-photosite residuals: compensation must cut the assembly's error
    /// at least threefold, and the reversed sign must make it worse.
    #[test]
    fn compensation_undoes_measured_member_displacement() {
        let offsets = [(0, 0), (0, -1), (1, -1), (1, 0)];
        let residuals = [[0.0, 0.0], [0.25, -0.1], [-0.2, 0.22], [0.1, 0.28]];
        let scene = |x: f64, y: f64, c: usize| {
            1000.0
                + 300.0 * (0.9 * x + 0.3 * c as f64).sin() * (0.7 * y).cos()
                + 200.0 * (0.45 * (x + y)).sin()
        };
        let (w, rows) = (40usize, 12usize);
        let y0 = 5isize;
        // Raw assembly: each colour from the member site_members names,
        // sampled at x - r_k.
        let raw: Vec<[f32; 3]> = (0..rows + 2)
            .flat_map(|e| (0..w).map(move |x| (e, x)))
            .map(|(e, x)| {
                let y = y0 - 1 + e as isize;
                let sm = site_members(&offsets, x as isize, y);
                let at = |k: usize, c: usize| {
                    scene(x as f64 - residuals[k][0], y as f64 - residuals[k][1], c) as f32
                };
                [
                    at(sm[0], 0),
                    0.5 * (at(sm[1], 1) + at(sm[2], 1)),
                    at(sm[3], 2),
                ]
            })
            .collect();
        let rms = |sign: Option<f32>| {
            let (mut r, mut g, mut b) = (
                vec![0f32; rows * w],
                vec![0f32; rows * w],
                vec![0f32; rows * w],
            );
            match sign {
                Some(s) => compensate_rows(
                    &raw,
                    w,
                    rows,
                    y0,
                    &offsets,
                    &residuals,
                    s,
                    [&mut r, &mut g, &mut b],
                ),
                None => {
                    for k in 0..rows {
                        for x in 0..w {
                            let v = raw[(k + 1) * w + x];
                            (r[k * w + x], g[k * w + x], b[k * w + x]) = (v[0], v[1], v[2]);
                        }
                    }
                }
            }
            let mut e = 0f64;
            let mut n = 0f64;
            for k in 0..rows {
                for x in 1..w - 1 {
                    let y = (y0 + k as isize) as f64;
                    for (c, plane) in [&r, &g, &b].iter().enumerate() {
                        let d = f64::from(plane[k * w + x]) - scene(x as f64, y, c);
                        e += d * d;
                        n += 1.0;
                    }
                }
            }
            (e / n).sqrt()
        };
        let (none, fixed, placebo) = (rms(None), rms(Some(1.0)), rms(Some(-1.0)));
        // First order: what is left is the second-order term, about
        // (2 pi f r)^2 / 2 of the detail (here 30 -> 8 DN rms).
        assert!(
            fixed < none / 3.0,
            "uncompensated {none}, compensated {fixed}"
        );
        assert!(
            placebo > none * 1.5,
            "uncompensated {none}, reversed {placebo}"
        );
    }
}
