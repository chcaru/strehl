//! Geometric registration of a focus bracket: the stage the shipped merge does
//! not have.
//!
//! `strehl-cli`'s stack path is `decode -> calibrate -> focus measure -> merge`
//! with **no** alignment step, so every frame is combined in sensor
//! coordinates. On a macro bracket that is not a small omission: as focus moves
//! the magnification moves with it (focus breathing), so the frames are at
//! genuinely different scales and the misregistration grows linearly with
//! radius from the centre of expansion.
//!
//! # What is modelled
//!
//! A similarity, and only a similarity: `p' = a*p + b` on plane coordinates
//! taken **relative to the plane centre**, with `a` complex (uniform scale and
//! rotation) and `b` complex (translation). That is four real parameters. It is
//! the right first-order model for breathing on a fixed camera, and
//! [`CaptureMode::Rail`](crate::CaptureMode::Rail) is explicitly *not* covered:
//! rail motion produces depth-dependent parallax, for which no global 2D
//! transform exists.
//!
//! # The two halves, and why they are separate
//!
//! - **Measure** ([`align_pair`]) — tiled zero-mean normalised cross
//!   correlation with parabolic sub-pixel refinement, least-squares fit of the
//!   similarity to the tile displacement field, one MAD outlier pass. This
//!   measures **one pair, directly**. Nothing here composes one pair's answer
//!   into another's.
//! - **Solve** ([`solve_global`], [`solve_poly`]) — one weighted complex linear
//!   least squares over *all* the measured edges at once, producing a transform
//!   per frame relative to frame 0.
//!
//! The separation is load-bearing. `AGENTS.md` rule 6 forbids chaining
//! adjacent-frame estimates, because a per-step bias compounds; the measured
//! penalty for doing it anyway is large (M10 fact: `S1-hops1` scores 40.342
//! plane px held-out where the global solve scores 6.758). A global solve over
//! a graph that contains cycles is the alternative, and it is only as good as
//! the long-span edges that create those cycles.
//!
//! # Units
//!
//! Everything in this module is in **plane pixels** — the half-resolution CFA
//! plane of [`PlaneGeometry`], where one plane px spans two sensor px. Errors
//! are quoted as *corner error*: the largest distance, over the four plane
//! corners, between where two similarities send that corner
//! ([`Similarity::corner_err`]). The corner is where a scale error is largest,
//! so this is the conservative statistic.
//!
//! # What this module deliberately does not do
//!
//! It does not resample anything into an aligned buffer. `AGENTS.md` rule 2:
//! the transform is applied by *gathering* at the point of consumption
//! ([`sample_catmull_rom`] and friends), never by materialising a warped copy
//! of every frame. Interpolation is a lowpass, and applying it twice — once to
//! register, once to output — throws away exactly the fine detail this project
//! exists to keep.
//!
//! # Provenance
//!
//! The estimator is a behaviour-preserving port of the one validated in
//! `experiments/m3-drift` and re-used by `experiments/m10-deep-align`; the
//! global solvers are a first Rust implementation of what M10 prototyped in
//! Python (`experiments/m10-deep-align/m10_lib.py`). Neither had ever been in
//! `crates/` before. Deviations from those references are listed in
//! `docs/research/M86-alignment.md` §"Port fidelity"; the two that matter are
//! that transforms are carried in `f64` rather than `f32`, and that the linear
//! solves use normal equations with a Hermitian Cholesky factorisation and
//! iterative refinement rather than NumPy's SVD-based `lstsq`.

use crate::plane::PlaneGeometry;
use std::collections::VecDeque;
use std::ops::{Add, Mul, Neg, Sub};

// ===========================================================================
// complex arithmetic
// ===========================================================================

/// A complex number in `f64`.
///
/// Written out rather than pulled in as a dependency: this crate's whole
/// dependency set is `thiserror` and `anyhow`, and the operations needed here
/// are a dozen lines.
#[derive(Clone, Copy, Debug, Default, PartialEq)]
pub struct Cx {
    pub re: f64,
    pub im: f64,
}

impl Cx {
    pub const ZERO: Cx = Cx { re: 0.0, im: 0.0 };
    pub const ONE: Cx = Cx { re: 1.0, im: 0.0 };

    #[inline]
    pub const fn new(re: f64, im: f64) -> Self {
        Self { re, im }
    }

    #[inline]
    pub const fn real(re: f64) -> Self {
        Self { re, im: 0.0 }
    }

    #[inline]
    pub const fn conj(self) -> Self {
        Self {
            re: self.re,
            im: -self.im,
        }
    }

    /// `|z|^2`. Preferred over [`Cx::abs`] wherever the square root is not
    /// needed, both for speed and because it cannot overflow to infinity as
    /// early.
    #[inline]
    pub fn norm_sq(self) -> f64 {
        self.re * self.re + self.im * self.im
    }

    #[inline]
    pub fn abs(self) -> f64 {
        self.re.hypot(self.im)
    }

    #[inline]
    pub fn scale(self, s: f64) -> Self {
        Self {
            re: self.re * s,
            im: self.im * s,
        }
    }

    /// `1/z`, or `None` at the origin.
    #[inline]
    pub fn recip(self) -> Option<Self> {
        let d = self.norm_sq();
        if d == 0.0 || !d.is_finite() {
            return None;
        }
        Some(Self {
            re: self.re / d,
            im: -self.im / d,
        })
    }

    /// `self / rhs`, or `None` when `rhs` is zero.
    #[inline]
    pub fn divide(self, rhs: Self) -> Option<Self> {
        rhs.recip().map(|r| self * r)
    }

    /// Principal branch of the complex logarithm.
    ///
    /// Safe for every use in this module: the scale factors it is applied to
    /// satisfy `|a - 1| < 0.1` over a whole deep bracket, so the argument never
    /// approaches the branch cut and no unwrapping is needed.
    #[inline]
    pub fn ln(self) -> Self {
        Self {
            re: self.abs().ln(),
            im: self.im.atan2(self.re),
        }
    }

    #[inline]
    pub fn exp(self) -> Self {
        let m = self.re.exp();
        Self {
            re: m * self.im.cos(),
            im: m * self.im.sin(),
        }
    }

    #[inline]
    pub fn is_finite(self) -> bool {
        self.re.is_finite() && self.im.is_finite()
    }
}

impl Add for Cx {
    type Output = Cx;
    #[inline]
    fn add(self, r: Cx) -> Cx {
        Cx::new(self.re + r.re, self.im + r.im)
    }
}

impl Sub for Cx {
    type Output = Cx;
    #[inline]
    fn sub(self, r: Cx) -> Cx {
        Cx::new(self.re - r.re, self.im - r.im)
    }
}

impl Mul for Cx {
    type Output = Cx;
    #[inline]
    fn mul(self, r: Cx) -> Cx {
        Cx::new(
            self.re * r.re - self.im * r.im,
            self.re * r.im + self.im * r.re,
        )
    }
}

impl Neg for Cx {
    type Output = Cx;
    #[inline]
    fn neg(self) -> Cx {
        Cx::new(-self.re, -self.im)
    }
}

// ===========================================================================
// similarity algebra
// ===========================================================================

/// A similarity transform on plane coordinates relative to the plane centre:
/// `p' = a*p + b`.
///
/// `a = (1 + g) + i*rot` carries scale and rotation together; `b = ax + i*ay`
/// is the translation. Holding them as one complex pair rather than four reals
/// is not cosmetic — it is what makes the edge constraints
/// `A_j = a_ij * A_i` and `B_j = a_ij * B_i + b_ij` **linear**, and therefore
/// what turns the whole bundle adjustment into a single linear least squares
/// with no iteration over the geometry.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Similarity {
    pub a: Cx,
    pub b: Cx,
}

/// The same transform written as the four real parameters the estimator solves
/// for, and the form the edge CSVs are stored in.
#[derive(Clone, Copy, Debug, Default, PartialEq)]
pub struct SimilarityParams {
    /// Translation, x, plane px.
    pub ax: f64,
    /// Translation, y, plane px.
    pub ay: f64,
    /// Scale minus one. `+0.01` is a 1% magnification.
    pub g: f64,
    /// Rotation in radians, small-angle (it is the imaginary part of `a`).
    pub rot: f64,
}

impl Similarity {
    pub const IDENTITY: Similarity = Similarity {
        a: Cx::ONE,
        b: Cx::ZERO,
    };

    #[inline]
    pub fn from_params(p: SimilarityParams) -> Self {
        Self {
            a: Cx::new(1.0 + p.g, p.rot),
            b: Cx::new(p.ax, p.ay),
        }
    }

    #[inline]
    pub fn to_params(self) -> SimilarityParams {
        SimilarityParams {
            ax: self.b.re,
            ay: self.b.im,
            g: self.a.re - 1.0,
            rot: self.a.im,
        }
    }

    /// Uniform scale factor, `|a|`.
    #[inline]
    pub fn scale(self) -> f64 {
        self.a.abs()
    }

    /// Rotation angle in radians, `arg(a)`.
    #[inline]
    pub fn rotation(self) -> f64 {
        self.a.im.atan2(self.a.re)
    }

    /// Apply to a point already expressed relative to the plane centre.
    #[inline]
    pub fn apply(self, p: Cx) -> Cx {
        self.a * p + self.b
    }

    /// Apply to an absolute plane coordinate, given the plane centre.
    #[inline]
    pub fn apply_at(self, x: f64, y: f64, cx: f64, cy: f64) -> (f64, f64) {
        let q = self.apply(Cx::new(x - cx, y - cy));
        (q.re + cx, q.im + cy)
    }

    /// The **exact** inverse map: which plane point `(x, y)` came from.
    ///
    /// `q = a*p + b` inverts to `p = (q - b)/a`. Warping by `p - d(p)` instead,
    /// i.e. subtracting the forward displacement, is the *linearised* inverse
    /// and is wrong at second order: the error it plants at the plane corner is
    /// `g^2 * rho`, which at the 4.6% scale drift M10 measured across a
    /// 105-frame stack is 4.3 plane px — the same size as the effect being
    /// measured. Any control that warps a frame must use this.
    #[inline]
    pub fn invert(self) -> Option<Similarity> {
        let inv_a = self.a.recip()?;
        Some(Similarity {
            a: inv_a,
            b: -(self.b * inv_a),
        })
    }

    /// Apply `self` first, then `other`.
    #[inline]
    pub fn then(self, other: Similarity) -> Similarity {
        Similarity {
            a: self.a * other.a,
            b: other.a * self.b + other.b,
        }
    }

    /// The transform from frame `i` coordinates to frame `j` coordinates, given
    /// each frame's transform from frame 0.
    #[inline]
    pub fn relative(gi: Similarity, gj: Similarity) -> Option<Similarity> {
        Some(gi.invert()?.then(gj))
    }

    /// Largest difference, over the four plane corners, in where two
    /// similarities send that corner. Plane px.
    ///
    /// This is the reported statistic everywhere in M86 and everywhere in M10
    /// before it. It is deliberately *not* the quantity the least squares
    /// minimises — see [`Similarity::corner_err_rms`] — because the worst
    /// corner is the conservative choice.
    pub fn corner_err(self, other: Similarity, geom: PlaneGeometry) -> f64 {
        let da = self.a - other.a;
        let db = self.b - other.b;
        corners(geom)
            .into_iter()
            .map(|p| (da * p + db).abs())
            .fold(0.0f64, f64::max)
    }

    /// Root-mean-square corner difference, plane px.
    ///
    /// This *is* what the weighted least squares minimises, because the corner
    /// set is symmetric about the plane centre — `sum(p) = 0` and
    /// `mean|p|^2 = rho^2` — so the cross term vanishes identically and
    ///
    /// ```text
    /// mean_corners |da*p + db|^2  ==  rho^2 |da|^2 + |db|^2
    /// ```
    ///
    /// `similarity_rms_identity_holds` checks that numerically rather than
    /// taking it on trust.
    pub fn corner_err_rms(self, other: Similarity, geom: PlaneGeometry) -> f64 {
        let da = self.a - other.a;
        let db = self.b - other.b;
        let s: f64 = corners(geom)
            .into_iter()
            .map(|p| (da * p + db).norm_sq())
            .sum();
        (s / 4.0).sqrt()
    }

    /// Corner error split into its scale/rotation part and its translation
    /// part: `(rho*|da|, |db|)`.
    ///
    /// Reported separately because the two have different error mechanisms.
    /// `da` is where pixel locking's compounding bias lands and where focus
    /// breathing lives; `db` is a rigid offset and carries neither.
    pub fn corner_err_parts(self, other: Similarity, geom: PlaneGeometry) -> (f64, f64) {
        let da = self.a - other.a;
        let db = self.b - other.b;
        (corner_radius(geom) * da.abs(), db.abs())
    }
}

/// The four plane corners as complex offsets from the plane centre.
pub fn corners(geom: PlaneGeometry) -> [Cx; 4] {
    let (w, h) = (geom.width as f64, geom.height as f64);
    let (cx, cy) = (w * 0.5, h * 0.5);
    [
        Cx::new(-cx, -cy),
        Cx::new(w - cx, -cy),
        Cx::new(-cx, h - cy),
        Cx::new(w - cx, h - cy),
    ]
}

/// Half-diagonal of the plane: the radius at which every corner-error figure in
/// this module and in M10 is quoted.
pub fn corner_radius(geom: PlaneGeometry) -> f64 {
    (geom.width as f64).hypot(geom.height as f64) * 0.5
}

// ===========================================================================
// plane views and the decimation pyramid
// ===========================================================================

/// A borrowed rectangular `f32` plane.
///
/// Distinct from [`PlaneGeometry`] because the estimator also works on
/// *decimated* copies, whose dimensions are not `active / 2` and so cannot be
/// built with [`PlaneGeometry::from_active`].
#[derive(Clone, Copy, Debug)]
pub struct PlaneRef<'a> {
    data: &'a [f32],
    width: usize,
    height: usize,
}

impl<'a> PlaneRef<'a> {
    /// `None` unless `data` is exactly `width * height` samples, so that no
    /// hot loop has to re-check the invariant.
    pub fn new(data: &'a [f32], width: usize, height: usize) -> Option<Self> {
        if width == 0 || height == 0 || data.len() != width.checked_mul(height)? {
            return None;
        }
        Some(Self {
            data,
            width,
            height,
        })
    }

    /// A view over a full-resolution CFA plane.
    pub fn from_geometry(data: &'a [f32], geom: PlaneGeometry) -> Option<Self> {
        Self::new(data, geom.width, geom.height)
    }

    #[inline]
    pub fn width(&self) -> usize {
        self.width
    }

    #[inline]
    pub fn height(&self) -> usize {
        self.height
    }

    #[inline]
    pub fn data(&self) -> &'a [f32] {
        self.data
    }

    #[inline]
    pub fn geometry(&self) -> PlaneGeometry {
        PlaneGeometry {
            width: self.width,
            height: self.height,
        }
    }

    #[inline]
    pub fn at(&self, x: usize, y: usize) -> f32 {
        self.data[y * self.width + x]
    }
}

/// An owned rectangular `f32` plane, used for the decimated pyramid levels.
#[derive(Clone, Debug)]
pub struct PlaneBuf {
    pub data: Vec<f32>,
    pub width: usize,
    pub height: usize,
}

impl PlaneBuf {
    pub fn as_ref(&self) -> PlaneRef<'_> {
        PlaneRef {
            data: &self.data,
            width: self.width,
            height: self.height,
        }
    }
}

/// Box-average decimation by an integer factor.
///
/// A box average, not a subsample: the coarse levels exist to bring the fine
/// correlation into capture range, and subsampling would alias the very
/// high-frequency detail that makes a macro frame correlate.
pub fn downsample(p: PlaneRef<'_>, factor: usize) -> Option<PlaneBuf> {
    if factor == 0 {
        return None;
    }
    let (w, h) = (p.width / factor, p.height / factor);
    if w == 0 || h == 0 {
        return None;
    }
    let mut out = vec![0f32; w * h];
    let inv = 1.0 / (factor * factor) as f32;
    for (y, row) in out.chunks_mut(w).enumerate() {
        for (x, o) in row.iter_mut().enumerate() {
            let mut s = 0f32;
            for dy in 0..factor {
                let base = (y * factor + dy) * p.width + x * factor;
                for dx in 0..factor {
                    s += p.data[base + dx];
                }
            }
            *o = s * inv;
        }
    }
    Some(PlaneBuf {
        data: out,
        width: w,
        height: h,
    })
}

/// Decimated copies of one plane, at the factors a configuration asks for.
///
/// Built once per frame and reused across every pair that frame takes part in.
/// On a 299-frame stack the pair set is in the hundreds, so rebuilding the
/// pyramid per pair would dominate the cost.
#[derive(Clone, Debug)]
pub struct AlignPyramid {
    pub factors: Vec<usize>,
    pub levels: Vec<PlaneBuf>,
}

impl AlignPyramid {
    pub fn build(p: PlaneRef<'_>, cfg: &AlignConfig) -> Option<Self> {
        let mut levels = Vec::with_capacity(cfg.coarse_factors.len());
        for f in &cfg.coarse_factors {
            levels.push(downsample(p, *f)?);
        }
        Some(Self {
            factors: cfg.coarse_factors.clone(),
            levels,
        })
    }

    /// Total decimated samples held, for memory accounting by the caller.
    pub fn samples(&self) -> usize {
        self.levels.iter().map(|l| l.data.len()).sum()
    }
}

/// One frame as the estimator wants it: the full plane plus its pyramid.
#[derive(Clone, Copy)]
pub struct AlignFrame<'a> {
    pub plane: PlaneRef<'a>,
    pub pyramid: &'a AlignPyramid,
}

// ===========================================================================
// the pairwise estimator
// ===========================================================================

/// Estimator configuration.
#[derive(Clone, Debug)]
pub struct AlignConfig {
    /// Decimation factors for the coarse ladder, largest first.
    pub coarse_factors: Vec<usize>,
    pub coarse_tile: usize,
    pub coarse_grid: (usize, usize),
    pub coarse_radius: i32,
    pub fine_tile: usize,
    pub fine_grid: (usize, usize),
    pub fine_radius: i32,
    /// Inset of the anchor grid from the plane edge, plane px.
    pub margin: usize,
    /// Minimum mean-square of the zero-mean reference tile, in DN^2, below
    /// which a tile is refused as featureless.
    pub min_contrast: f32,
    /// Minimum NCC peak for a tile to be believed.
    pub min_peak: f32,
    /// Minimum surviving tiles for a stage to return a fit.
    pub min_tiles: usize,
    /// MAD outlier cut, in MADs above the median residual.
    pub outlier_mads: f32,
    /// How many times each stage may re-seed itself from its own fit and
    /// re-search.
    ///
    /// `1` is the single-pass estimator M3 published, reproduced bit for bit.
    ///
    /// A stage searches `±radius` about the offset its *seed* predicts, so a
    /// tile is only measurable where the seed is already nearly right. The
    /// residual a wrong seed leaves at a tile grows with that tile's lever arm,
    /// `|residual| ~ |dg| * |u|`, so the tiles that fall outside the window
    /// first are the **corner** tiles — exactly the tiles that carry the scale
    /// signal. The survivors are the low-lever central tiles, whose
    /// displacements the seed already predicts, so the refit cannot move far
    /// from the seed. That is a self-confirming loop, and on `bee-3-cpl` M103
    /// measured it costing between 20% and 89% of the true scale, worsening
    /// monotonically with baseline.
    ///
    /// Re-seeding breaks the loop: each pass places the window closer to the
    /// truth, so border-refused tiles return and the lever arm recovers. Passes
    /// stop early once the fit stops moving, so a pair whose seed was already
    /// good costs one pass and is unchanged.
    pub fine_iters: usize,
    /// Resample each moving tile through the current seed before correlating,
    /// so the two tiles are compared at matched scale and rotation.
    ///
    /// [`ncc_tile`] searches **translations only**. Under a scale difference
    /// `s` a tile of side `t` is stretched by `t*(1-s)` across its own width,
    /// and no translation can undo that: at the 14.3% end-to-end scale of
    /// `bee-3-cpl` a 128 px tile is mismatched by 18.3 px, which no search
    /// window can recover because the defect is *inside* the tile. Widening the
    /// window makes this worse, not better — M103 measured the wide config
    /// over-shooting to 1.27 of truth at span 256 while the default under-shot
    /// to 0.11.
    ///
    /// Warping the moving tile through the seed removes the mismatch by
    /// construction, leaving a genuine translation for the search to find. The
    /// cost is one bilinear resample of a `(tile + 2*radius)^2` patch per tile
    /// per pass, against the `(2*radius+1)^2 * tile^2` multiply-adds the
    /// correlation already spends — under 1%.
    pub warp_tiles: bool,
}

impl AlignConfig {
    /// The estimator M3 published and M6 used, verbatim.
    pub fn shallow() -> Self {
        Self {
            coarse_factors: vec![8],
            coarse_tile: 32,
            coarse_grid: (8, 6),
            coarse_radius: 10,
            fine_tile: 128,
            fine_grid: (12, 8),
            fine_radius: 6,
            margin: 10,
            min_contrast: 4.0,
            min_peak: 0.5,
            min_tiles: 8,
            outlier_mads: 3.0,
            fine_iters: 1,
            warp_tiles: false,
        }
    }

    /// [`AlignConfig::shallow`] with the anchor grid inset far enough that a
    /// tile survives the corner drift a deep stack carries.
    ///
    /// The margin is the one parameter that must track stack depth. M10 sized
    /// it at 96 plane px for the 89 px of corner drift a 105-frame bracket
    /// showed; leaving it at 10 px censors exactly the high-lever-arm corner
    /// tiles on long-span pairs, which are the tiles the scale estimate rests
    /// on. Deeper stacks drift further — use [`AlignConfig::with_margin`] with
    /// a *measured* drift, do not assume 96 transfers.
    pub fn deep() -> Self {
        Self {
            margin: 96,
            ..Self::shallow()
        }
    }

    /// A deeper coarse ladder and a wider fine search, for pairs whose baseline
    /// is long enough that the default capture range fails.
    pub fn wide() -> Self {
        Self {
            coarse_factors: vec![32, 16, 8],
            coarse_radius: 12,
            fine_radius: 12,
            margin: 96,
            ..Self::shallow()
        }
    }

    pub fn with_margin(self, margin: usize) -> Self {
        Self { margin, ..self }
    }

    /// [`AlignConfig::deep`] with the two capture defects M103 measured closed:
    /// the stage re-seeds itself until it stops moving, and each moving tile is
    /// warped through the current seed before correlating.
    ///
    /// Both are off by default because turning them on changes every number the
    /// estimator has ever produced. See [`AlignConfig::fine_iters`] and
    /// [`AlignConfig::warp_tiles`] for what each one is for, and
    /// `docs/research/M103-halfdrift.md` for the measurements that set them.
    ///
    /// `fine_iters` is 8 because that is where `bee-3-cpl`'s longest baseline
    /// converged with margin, not because 8 is a round number; passes stop as
    /// soon as the corner moves less than [`FINE_CONVERGE_PX`], so short
    /// baselines pay for one or two.
    pub fn iterated() -> Self {
        Self {
            fine_iters: 8,
            warp_tiles: true,
            ..Self::deep()
        }
    }

    /// [`AlignConfig::iterated`] with the deeper coarse ladder of
    /// [`AlignConfig::wide`], for stacks whose end-to-end drift exceeds what a
    /// single 1/8 coarse level can capture.
    ///
    /// # Do not adopt this as a default on the strength of an end-to-end number
    ///
    /// M103's first arm reported that this config takes `bee-3-cpl`'s
    /// **end-to-end** residual from 150.3 plane px to 2.9, and recommended it
    /// become the default. **That recommendation is withdrawn**, by M103's own
    /// later measurement, and the reason generalises well past this function.
    ///
    /// The merge does not gather frames end to end. It gathers each frame at its
    /// own `a_k`, so what reaches the photograph is *per-frame placement*, and
    /// the two are very nearly independent. Scored against an independent RAW
    /// ladder of 39 rungs, in the gauge the merge actually uses (`reference
    /// 149`), mean per-frame placement error on `bee-3-cpl` is:
    ///
    /// | config | end-to-end residual | per-frame placement |
    /// |---|---:|---:|
    /// | [`AlignConfig::deep`], as shipped | 150.3 px | 36.4 px |
    /// | this one | 2.9 px | 37.5 px |
    ///
    /// A fifty-fold improvement in the headline number bought nothing where it
    /// counts, and three separate instruments then agreed the render did not
    /// change. Worse, this config *absorbs* the end-to-end shortfall, so the
    /// scalar gain correction that is worth 38% of per-frame placement error on
    /// the shipped solve makes this one **worse** (37.5 -> 70.0 px at 1.84).
    ///
    /// The iteration and tile warping are real and are measured to work; it is
    /// the *bar* that was wrong. Anyone changing a default here should score it
    /// per frame, not end to end. See `docs/research/M103-halfdrift.md` Section 16.
    pub fn iterated_wide() -> Self {
        Self {
            fine_iters: 8,
            warp_tiles: true,
            ..Self::wide()
        }
    }
}

/// Corner movement, plane px, below which an iterated stage stops re-seeding.
///
/// Well under the ~0.1 px the subpixel parabola is worth, so stopping here
/// costs nothing measurable, and small enough that a pair still drifting is not
/// mistaken for a converged one.
pub const FINE_CONVERGE_PX: f64 = 0.02;

/// Why one tile produced no displacement.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum TileStatus {
    Ok,
    /// The reference tile is flat: nothing to correlate.
    LowContrast,
    /// The best correlation peak is below the floor. On a focus bracket this is
    /// the honest signature of a wide defocus baseline, not a bug.
    LowPeak,
    /// The peak sits on the edge of the search window, so the true peak may be
    /// outside it and the parabolic refinement is meaningless.
    Border,
    /// No candidate offset kept the template inside the moving plane.
    Oob,
}

/// One tile's measurement.
#[derive(Clone, Copy, Debug)]
pub struct TileMeasurement {
    pub status: TileStatus,
    /// Mean square of the zero-mean reference tile, DN^2 — what the contrast
    /// floor tests.
    pub contrast: f32,
    pub dx: f32,
    pub dy: f32,
    pub peak: f32,
}

impl TileMeasurement {
    fn failed(status: TileStatus, contrast: f32) -> Self {
        Self {
            status,
            contrast,
            dx: f32::NAN,
            dy: f32::NAN,
            peak: f32::NAN,
        }
    }
}

/// A tile displacement: the tile's offset from the plane centre, and the
/// displacement measured there.
#[derive(Clone, Copy, Debug)]
pub struct Observation {
    pub ux: f32,
    pub uy: f32,
    pub dx: f32,
    pub dy: f32,
}

fn parabola(l: f32, c: f32, r: f32) -> f32 {
    if !l.is_finite() || !r.is_finite() {
        return 0.0;
    }
    let d = l - 2.0 * c + r;
    if d.abs() < 1e-12 {
        return 0.0;
    }
    let o = 0.5 * (l - r) / d;
    if o.abs() > 1.0 { 0.0 } else { o }
}

/// Where and how one tile is correlated.
#[derive(Clone, Copy, Debug)]
pub struct TileProbe {
    /// Top-left of the reference tile, plane px.
    pub tx: usize,
    pub ty: usize,
    /// Tile side, plane px.
    pub size: usize,
    /// Predicted displacement at the tile centre, used to place the search
    /// window.
    pub predicted: (f32, f32),
    /// Half-width of the square search window, plane px.
    pub radius: i32,
}

/// Zero-mean normalised cross correlation of one reference tile against the
/// moving plane, searching a square window around the predicted offset.
///
/// The correlation is deliberately kept in `f32`: it is the arithmetic the
/// prior milestones' numbers were produced with, and promoting it would change
/// results at a level that cannot be distinguished from a real improvement
/// without re-measuring everything.
pub fn ncc_tile(
    reference: PlaneRef<'_>,
    moving: PlaneRef<'_>,
    probe: TileProbe,
    cfg: &AlignConfig,
) -> TileMeasurement {
    let TileProbe {
        tx,
        ty,
        size: ts,
        predicted: (px, py),
        radius,
    } = probe;
    if ts == 0 || tx + ts > reference.width || ty + ts > reference.height {
        return TileMeasurement::failed(TileStatus::Oob, f32::NAN);
    }

    let mut a = vec![0f32; ts * ts];
    let mut mean = 0f32;
    for y in 0..ts {
        let row = (ty + y) * reference.width + tx;
        for x in 0..ts {
            let v = reference.data[row + x];
            a[y * ts + x] = v;
            mean += v;
        }
    }
    mean /= (ts * ts) as f32;
    let mut sa = 0f32;
    for v in a.iter_mut() {
        *v -= mean;
        sa += *v * *v;
    }
    let contrast = sa / (ts * ts) as f32;
    if contrast <= cfg.min_contrast {
        return TileMeasurement::failed(TileStatus::LowContrast, contrast);
    }

    let (bx, by) = (px.round() as i32, py.round() as i32);
    let n = (2 * radius + 1) as usize;
    let mut scores = vec![f32::NEG_INFINITY; n * n];
    let (mut best, mut bi, mut bj) = (f32::NEG_INFINITY, 0usize, 0usize);

    for j in -radius..=radius {
        for i in -radius..=radius {
            let ox = tx as i32 + bx + i;
            let oy = ty as i32 + by + j;
            if ox < 0
                || oy < 0
                || ox as usize + ts > moving.width
                || oy as usize + ts > moving.height
            {
                continue;
            }
            let (ox, oy) = (ox as usize, oy as usize);
            let mut mb = 0f32;
            for y in 0..ts {
                let row = (oy + y) * moving.width + ox;
                for x in 0..ts {
                    mb += moving.data[row + x];
                }
            }
            mb /= (ts * ts) as f32;
            let (mut num, mut sb) = (0f32, 0f32);
            for y in 0..ts {
                let row = (oy + y) * moving.width + ox;
                for x in 0..ts {
                    let bv = moving.data[row + x] - mb;
                    num += a[y * ts + x] * bv;
                    sb += bv * bv;
                }
            }
            if sb <= 1e-6 {
                continue;
            }
            let s = num / (sa * sb).sqrt();
            let (ii, jj) = ((i + radius) as usize, (j + radius) as usize);
            scores[jj * n + ii] = s;
            if s > best {
                best = s;
                bi = ii;
                bj = jj;
            }
        }
    }

    if !best.is_finite() {
        return TileMeasurement::failed(TileStatus::Oob, contrast);
    }
    if best < cfg.min_peak {
        let mut m = TileMeasurement::failed(TileStatus::LowPeak, contrast);
        m.peak = best;
        return m;
    }
    if bi == 0 || bj == 0 || bi == n - 1 || bj == n - 1 {
        let mut m = TileMeasurement::failed(TileStatus::Border, contrast);
        m.peak = best;
        return m;
    }
    let sc = |i: usize, j: usize| scores[j * n + i];
    let ox = parabola(sc(bi - 1, bj), sc(bi, bj), sc(bi + 1, bj));
    let oy = parabola(sc(bi, bj - 1), sc(bi, bj), sc(bi, bj + 1));
    TileMeasurement {
        status: TileStatus::Ok,
        contrast,
        dx: (bx + bi as i32 - radius) as f32 + ox,
        dy: (by + bj as i32 - radius) as f32 + oy,
        peak: best,
    }
}

/// Bilinear sample of `plane` at a fractional coordinate, refusing rather than
/// clamping outside it.
///
/// [`sample_bilinear`] clamps, which is right for a renderer and wrong here: a
/// clamped sample is a fabricated correlation peak, and because a warped tile
/// leaves the plane at the *corners* first, the fabrication would land
/// preferentially on the high-lever tiles this whole mechanism turns on.
#[inline]
fn sample_bilinear_strict(plane: PlaneRef<'_>, x: f64, y: f64) -> Option<f32> {
    let x0 = x.floor();
    let y0 = y.floor();
    if x0 < 0.0 || y0 < 0.0 {
        return None;
    }
    let (ix, iy) = (x0 as usize, y0 as usize);
    if ix + 1 >= plane.width || iy + 1 >= plane.height {
        return None;
    }
    let (fx, fy) = ((x - x0) as f32, (y - y0) as f32);
    let r0 = iy * plane.width + ix;
    let r1 = r0 + plane.width;
    let a = plane.data[r0];
    let b = plane.data[r0 + 1];
    let c = plane.data[r1];
    let d = plane.data[r1 + 1];
    let top = a + (b - a) * fx;
    let bot = c + (d - c) * fx;
    Some(top + (bot - top) * fy)
}

/// [`ncc_tile`], but the moving tile is first resampled through `warp` so that
/// only the *residual* translation is searched.
///
/// # Why this exists
///
/// [`ncc_tile`] slices an axis-aligned window out of the moving plane and slides
/// it. That is only a valid model of the pair when the two frames differ by a
/// translation. Under a scale difference the moving tile is a *stretched* copy
/// of the reference tile, and the stretch across one tile of side `t` is
/// `t*|1-s|` — 18.3 plane px for the 128 px tile and 14.3% end-to-end scale of
/// `bee-3-cpl`. No translation removes that. The correlation peak is broadened
/// and pulled toward whichever part of the tile happens to dominate, the peak
/// height falls below `min_peak`, and the tile is either refused or believed at
/// a biased offset.
///
/// Sampling the moving plane along the reference tile's *warped* grid removes
/// the stretch by construction. What is left is a real translation, which is
/// what the search is entitled to assume.
///
/// # Coordinates
///
/// The patch is built on the reference tile's own lattice, extended by `radius`
/// on every side, so search offset `(i, j)` is a shift in *reference* px. The
/// same offset in moving px is `a * (i, j)`, and that is what is composed into
/// the returned displacement — dropping the `a` would re-introduce a scale
/// error of `|1-s|` times the residual.
pub fn ncc_tile_warped(
    reference: PlaneRef<'_>,
    moving: PlaneRef<'_>,
    probe: TileProbe,
    warp: SimilarityParams,
    cfg: &AlignConfig,
) -> TileMeasurement {
    let TileProbe {
        tx,
        ty,
        size: ts,
        predicted: (px, py),
        radius,
    } = probe;
    if ts == 0 || tx + ts > reference.width || ty + ts > reference.height {
        return TileMeasurement::failed(TileStatus::Oob, f32::NAN);
    }

    let mut a = vec![0f32; ts * ts];
    let mut mean = 0f32;
    for y in 0..ts {
        let row = (ty + y) * reference.width + tx;
        for x in 0..ts {
            let v = reference.data[row + x];
            a[y * ts + x] = v;
            mean += v;
        }
    }
    mean /= (ts * ts) as f32;
    let mut sa = 0f32;
    for v in a.iter_mut() {
        *v -= mean;
        sa += *v * *v;
    }
    let contrast = sa / (ts * ts) as f32;
    if contrast <= cfg.min_contrast {
        return TileMeasurement::failed(TileStatus::LowContrast, contrast);
    }

    // Where this tile's centre lands under the seed, and the linear part that
    // carries the tile's own lattice with it.
    let half = ts as f64 * 0.5;
    let mcx = tx as f64 + half + px as f64;
    let mcy = ty as f64 + half + py as f64;
    let (ar, ai) = (1.0 + warp.g, warp.rot);

    // Build the warped patch once, on the reference lattice extended by
    // `radius` each way, so the translation search below needs no resampling.
    let r = radius as usize;
    let np = ts + 2 * r;
    let mut patch = vec![0f32; np * np];
    for q in 0..np {
        let vy = q as f64 - r as f64 - half;
        for p in 0..np {
            let vx = p as f64 - r as f64 - half;
            let sx = mcx + ar * vx - ai * vy;
            let sy = mcy + ai * vx + ar * vy;
            match sample_bilinear_strict(moving, sx, sy) {
                Some(v) => patch[q * np + p] = v,
                None => return TileMeasurement::failed(TileStatus::Oob, contrast),
            }
        }
    }

    let n = (2 * radius + 1) as usize;
    let mut scores = vec![f32::NEG_INFINITY; n * n];
    let (mut best, mut bi, mut bj) = (f32::NEG_INFINITY, 0usize, 0usize);
    for jj in 0..n {
        for ii in 0..n {
            let mut mb = 0f32;
            for y in 0..ts {
                let row = (y + jj) * np + ii;
                for x in 0..ts {
                    mb += patch[row + x];
                }
            }
            mb /= (ts * ts) as f32;
            let (mut num, mut sb) = (0f32, 0f32);
            for y in 0..ts {
                let row = (y + jj) * np + ii;
                for x in 0..ts {
                    let bv = patch[row + x] - mb;
                    num += a[y * ts + x] * bv;
                    sb += bv * bv;
                }
            }
            if sb <= 1e-6 {
                continue;
            }
            let s = num / (sa * sb).sqrt();
            scores[jj * n + ii] = s;
            if s > best {
                best = s;
                bi = ii;
                bj = jj;
            }
        }
    }

    if !best.is_finite() {
        return TileMeasurement::failed(TileStatus::Oob, contrast);
    }
    if best < cfg.min_peak {
        let mut m = TileMeasurement::failed(TileStatus::LowPeak, contrast);
        m.peak = best;
        return m;
    }
    if bi == 0 || bj == 0 || bi == n - 1 || bj == n - 1 {
        let mut m = TileMeasurement::failed(TileStatus::Border, contrast);
        m.peak = best;
        return m;
    }
    let sc = |i: usize, j: usize| scores[j * n + i];
    let ox = parabola(sc(bi - 1, bj), sc(bi, bj), sc(bi + 1, bj));
    let oy = parabola(sc(bi, bj - 1), sc(bi, bj), sc(bi, bj + 1));
    // Residual in reference px, then carried into moving px through `a`.
    let rx = (bi as i32 - radius) as f64 + ox as f64;
    let ry = (bj as i32 - radius) as f64 + oy as f64;
    TileMeasurement {
        status: TileStatus::Ok,
        contrast,
        dx: (px as f64 + ar * rx - ai * ry) as f32,
        dy: (py as f64 + ai * rx + ar * ry) as f32,
        peak: best,
    }
}

/// 4x4 Gauss-Jordan with partial pivoting. `None` if the system is singular.
fn solve4(mut m: [[f64; 5]; 4]) -> Option<[f64; 4]> {
    for c in 0..4 {
        let mut p = c;
        for r in c + 1..4 {
            if m[r][c].abs() > m[p][c].abs() {
                p = r;
            }
        }
        if m[p][c].abs() < 1e-12 {
            return None;
        }
        m.swap(c, p);
        let d = m[c][c];
        for v in m[c].iter_mut() {
            *v /= d;
        }
        for r in 0..4 {
            if r != c {
                let f = m[r][c];
                let pivot = m[c];
                for (v, pv) in m[r].iter_mut().zip(pivot.iter()).skip(c) {
                    *v -= f * pv;
                }
            }
        }
    }
    Some([m[0][4], m[1][4], m[2][4], m[3][4]])
}

/// Least-squares similarity through a tile displacement field.
///
/// Two rows per observation — one per displacement component — in the unknowns
/// `(ax, ay, g, rot)`. Accumulated in `f64` because the normal matrix of a
/// 3516-px-wide plane has entries spanning ten orders of magnitude.
pub fn fit_similarity(obs: &[Observation]) -> Option<SimilarityParams> {
    let mut ata = [[0f64; 5]; 4];
    let mut add = |row: [f64; 4], b: f64| {
        for (i, ri) in row.iter().enumerate() {
            for (j, rj) in row.iter().enumerate() {
                ata[i][j] += ri * rj;
            }
            ata[i][4] += ri * b;
        }
    };
    for o in obs {
        let (ux, uy) = (o.ux as f64, o.uy as f64);
        add([1.0, 0.0, ux, -uy], o.dx as f64);
        add([0.0, 1.0, uy, ux], o.dy as f64);
    }
    let s = solve4(ata)?;
    Some(SimilarityParams {
        ax: s[0],
        ay: s[1],
        g: s[2],
        rot: s[3],
    })
}

/// Displacement this fit predicts at a point offset `(ux, uy)` from the plane
/// centre.
#[inline]
fn predicted_displacement(f: SimilarityParams, ux: f64, uy: f64) -> (f64, f64) {
    (f.ax + f.g * ux - f.rot * uy, f.ay + f.rot * ux + f.g * uy)
}

fn residuals(obs: &[Observation], f: SimilarityParams) -> Vec<f32> {
    obs.iter()
        .map(|o| {
            let (px, py) = predicted_displacement(f, o.ux as f64, o.uy as f64);
            let ex = o.dx as f64 - px;
            let ey = o.dy as f64 - py;
            (ex * ex + ey * ey).sqrt() as f32
        })
        .collect()
}

/// The outcome of one correlation stage.
#[derive(Clone, Debug)]
pub struct StageFit {
    pub fit: SimilarityParams,
    /// Tiles surviving the outlier pass.
    pub used: usize,
    /// Tiles attempted.
    pub total: usize,
    /// Tiles that correlated, before the outlier pass.
    pub raw_n: usize,
    /// RMS residual of the surviving tiles, plane px. The estimator's own
    /// statement of its precision.
    pub rms: f32,
    /// RMS radius of the surviving tiles: the lever arm the scale estimate
    /// actually rests on. Needed to turn a tile RMS into a corner-error
    /// standard error without assuming the grid.
    pub lever_rms: f32,
    /// Mean correlation peak over the surviving tiles.
    pub peak_mean: f32,
    /// Census of why tiles were refused.
    pub rejected: TileCensus,
}

impl StageFit {
    /// The fit as a transform.
    pub fn similarity(&self) -> Similarity {
        Similarity::from_params(self.fit)
    }
}

/// How many tiles each refusal reason accounted for.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct TileCensus {
    pub low_contrast: usize,
    pub low_peak: usize,
    pub border: usize,
    pub oob: usize,
    pub outlier: usize,
}

/// Why a pair produced no fit. Every variant is an honest refusal, not an
/// error: a focus bracket contains pairs whose defocus baseline is simply too
/// wide to correlate, and inventing a transform for those is the failure mode
/// that matters.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum AlignFailure {
    /// The plane is smaller than one tile plus twice the margin.
    GridTooSmall,
    /// Fewer than `min_tiles` tiles correlated at all.
    TooFewTiles { correlated: usize },
    /// The outlier pass took the survivors below `min_tiles`.
    TooFewAfterOutliers { survivors: usize },
    /// The normal matrix was singular — degenerate tile geometry.
    Singular,
    /// A coarse level of the pyramid failed, so the fine search was never
    /// brought into capture range.
    CoarseStageFailed { level: usize },
}

/// Anchor grid: `gx` by `gy` tile origins, inset by `margin` from every edge.
pub fn tile_grid(
    plane: PlaneRef<'_>,
    tile: usize,
    gx: usize,
    gy: usize,
    margin: usize,
) -> Option<Vec<(usize, usize)>> {
    if gx == 0 || gy == 0 {
        return None;
    }
    if plane.width < tile + 2 * margin || plane.height < tile + 2 * margin {
        return None;
    }
    let span_x = plane.width - tile - 2 * margin;
    let span_y = plane.height - tile - 2 * margin;
    let mut spots = Vec::with_capacity(gx * gy);
    for j in 0..gy {
        for i in 0..gx {
            let tx = margin + span_x * i / (gx - 1).max(1);
            let ty = margin + span_y * j / (gy - 1).max(1);
            spots.push((tx, ty));
        }
    }
    Some(spots)
}

/// One correlation stage: measure every tile, fit a similarity, drop outliers,
/// refit.
pub fn fit_stage(
    reference: PlaneRef<'_>,
    moving: PlaneRef<'_>,
    tile: usize,
    spots: &[(usize, usize)],
    radius: i32,
    seed: Option<SimilarityParams>,
    cfg: &AlignConfig,
) -> Result<StageFit, AlignFailure> {
    let (cx, cy) = (reference.width as f64 * 0.5, reference.height as f64 * 0.5);

    let mut obs: Vec<Observation> = Vec::with_capacity(spots.len());
    let mut peaks: Vec<f32> = Vec::with_capacity(spots.len());
    let mut census = TileCensus::default();

    for &(tx, ty) in spots {
        let mx = tx as f64 + tile as f64 * 0.5;
        let my = ty as f64 + tile as f64 * 0.5;
        let (px, py) = match seed {
            Some(s) => predicted_displacement(s, mx - cx, my - cy),
            None => (0.0, 0.0),
        };
        let tp = TileProbe {
            tx,
            ty,
            size: tile,
            predicted: (px as f32, py as f32),
            radius,
        };
        // Warping needs a seed to warp through. With no seed the two paths are
        // the same computation, so the plain one runs and the single-pass
        // estimator is reproduced exactly.
        let m = match (cfg.warp_tiles, seed) {
            (true, Some(s)) => ncc_tile_warped(reference, moving, tp, s, cfg),
            _ => ncc_tile(reference, moving, tp, cfg),
        };
        match m.status {
            TileStatus::Ok => {
                obs.push(Observation {
                    ux: (mx - cx) as f32,
                    uy: (my - cy) as f32,
                    dx: m.dx,
                    dy: m.dy,
                });
                peaks.push(m.peak);
            }
            TileStatus::LowContrast => census.low_contrast += 1,
            TileStatus::LowPeak => census.low_peak += 1,
            TileStatus::Border => census.border += 1,
            TileStatus::Oob => census.oob += 1,
        }
    }

    let total = spots.len();
    if obs.len() < cfg.min_tiles {
        return Err(AlignFailure::TooFewTiles {
            correlated: obs.len(),
        });
    }

    let f0 = fit_similarity(&obs).ok_or(AlignFailure::Singular)?;
    let res = residuals(&obs, f0);
    let raw_n = obs.len();

    let mut sorted = res.clone();
    sorted.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    let med = sorted[sorted.len() / 2];
    let mut devs: Vec<f32> = res.iter().map(|r| (r - med).abs()).collect();
    devs.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    let mad = devs[devs.len() / 2].max(1e-3);
    let cut = med + cfg.outlier_mads * 1.4826 * mad;

    let keep: Vec<bool> = res.iter().map(|r| *r <= cut).collect();
    let kept: Vec<Observation> = obs
        .iter()
        .zip(&keep)
        .filter(|(_, k)| **k)
        .map(|(o, _)| *o)
        .collect();
    census.outlier = raw_n - kept.len();
    if kept.len() < cfg.min_tiles {
        return Err(AlignFailure::TooFewAfterOutliers {
            survivors: kept.len(),
        });
    }
    let fit = fit_similarity(&kept).ok_or(AlignFailure::Singular)?;
    let kres = residuals(&kept, fit);
    let rms = (kres.iter().map(|r| r * r).sum::<f32>() / kres.len() as f32).sqrt();
    let lever_rms = (kept
        .iter()
        .map(|o| (o.ux * o.ux + o.uy * o.uy) as f64)
        .sum::<f64>()
        / kept.len() as f64)
        .sqrt() as f32;
    let peak_sum: f32 = peaks
        .iter()
        .zip(&keep)
        .filter(|(_, k)| **k)
        .map(|(p, _)| *p)
        .sum();
    let peak_mean = peak_sum / kept.len() as f32;

    Ok(StageFit {
        fit,
        used: kept.len(),
        total,
        raw_n,
        rms,
        lever_rms,
        peak_mean,
        rejected: census,
    })
}

/// [`fit_stage`], re-seeded from its own fit until the fit stops moving.
///
/// One pass is one Newton step from the seed, and it inherits the seed's blind
/// spot: tiles whose true offset the seed misses by more than `radius` are
/// refused, and because the miss grows with lever arm those are the corner
/// tiles the scale rests on. Re-seeding walks the window onto the truth, so
/// each pass recovers lever arm the last one censored.
///
/// Passes stop when the plane corner moves less than [`FINE_CONVERGE_PX`], and
/// a pass that *fails* leaves the previous fit standing rather than discarding
/// a good answer for a worse one.
fn fit_stage_iterated(
    reference: PlaneRef<'_>,
    moving: PlaneRef<'_>,
    tile: usize,
    spots: &[(usize, usize)],
    radius: i32,
    seed: Option<SimilarityParams>,
    cfg: &AlignConfig,
) -> Result<StageFit, AlignFailure> {
    let mut best = fit_stage(reference, moving, tile, spots, radius, seed, cfg)?;
    let hw = reference.width as f64 * 0.5;
    let hh = reference.height as f64 * 0.5;
    for _ in 1..cfg.fine_iters.max(1) {
        let prev = best.fit;
        let next = match fit_stage(reference, moving, tile, spots, radius, Some(prev), cfg) {
            Ok(n) => n,
            Err(_) => break,
        };
        let (dg, dr) = (next.fit.g - prev.g, next.fit.rot - prev.rot);
        let (dx, dy) = (next.fit.ax - prev.ax, next.fit.ay - prev.ay);
        let moved = [(-hw, -hh), (hw, -hh), (-hw, hh), (hw, hh)]
            .into_iter()
            .map(|(ux, uy)| {
                let ex = dx + dg * ux - dr * uy;
                let ey = dy + dr * ux + dg * uy;
                (ex * ex + ey * ey).sqrt()
            })
            .fold(0.0f64, f64::max);
        best = next;
        if moved < FINE_CONVERGE_PX {
            break;
        }
    }
    Ok(best)
}

/// Coarse-to-fine similarity fit of `moving` against `reference`.
///
/// The coarse ladder exists **only** to bring the fine search into capture
/// range; all accuracy comes from the fine stage, which correlates the two full
/// planes **directly**. No pair's fit is ever composed into another pair's, so
/// `AGENTS.md` rule 6 is not touched by the estimator itself — only a solver
/// can violate it.
pub fn align_pair(
    reference: AlignFrame<'_>,
    moving: AlignFrame<'_>,
    spots: &[(usize, usize)],
    cfg: &AlignConfig,
) -> Result<StageFit, AlignFailure> {
    let mut seed: Option<SimilarityParams> = None;
    for (li, f) in reference.pyramid.factors.iter().enumerate() {
        let rc = reference.pyramid.levels[li].as_ref();
        let mc = moving.pyramid.levels[li].as_ref();
        let cspots = tile_grid(
            rc,
            cfg.coarse_tile,
            cfg.coarse_grid.0,
            cfg.coarse_grid.1,
            cfg.coarse_radius as usize + 4,
        )
        .ok_or(AlignFailure::GridTooSmall)?;
        // Carry the previous level's translation down into this level's units.
        // Scale and rotation are dimensionless and carry unchanged.
        let lseed = seed.map(|s| SimilarityParams {
            ax: s.ax / *f as f64,
            ay: s.ay / *f as f64,
            ..s
        });
        let st = fit_stage_iterated(
            rc,
            mc,
            cfg.coarse_tile,
            &cspots,
            cfg.coarse_radius,
            lseed,
            cfg,
        )
        .map_err(|_| AlignFailure::CoarseStageFailed { level: li })?;
        seed = Some(SimilarityParams {
            ax: st.fit.ax * *f as f64,
            ay: st.fit.ay * *f as f64,
            ..st.fit
        });
    }
    fit_stage_iterated(
        reference.plane,
        moving.plane,
        cfg.fine_tile,
        spots,
        cfg.fine_radius,
        seed,
        cfg,
    )
}

// ===========================================================================
// weighted complex least squares
// ===========================================================================

/// One row of a complex least-squares system, held sparsely.
#[derive(Clone, Debug)]
struct LsRow {
    cols: Vec<(usize, Cx)>,
    rhs: Cx,
}

/// A weighted complex least-squares problem, solved by normal equations with a
/// Hermitian Cholesky factorisation and iterative refinement.
///
/// Why not a QR or an SVD, as NumPy's `lstsq` uses? Because every system in
/// this module has at most two non-zeros per row, so forming `A^H A` costs
/// `O(edges)` rather than `O(edges * n^2)`, and the factorisation of a dense
/// 298x298 Hermitian matrix is under ten megaflops. The price is a squared
/// condition number, which the refinement step below buys back.
///
/// The price that is *not* paid back is rank deficiency: `lstsq` silently
/// returns a minimum-norm answer for an under-determined system, which is how
/// M10 initially reported full coverage for frames that no edge constrained.
/// A Cholesky refuses instead, and callers here restrict the unknown set to the
/// connected component before solving so that refusal cannot happen for a
/// legitimate reason.
#[derive(Clone, Debug)]
struct LeastSquares {
    ncol: usize,
    rows: Vec<LsRow>,
}

impl LeastSquares {
    fn new(ncol: usize) -> Self {
        Self {
            ncol,
            rows: Vec::new(),
        }
    }

    fn push(&mut self, cols: Vec<(usize, Cx)>, rhs: Cx) {
        self.rows.push(LsRow { cols, rhs });
    }

    /// `A^H A` (lower triangle, row-major dense) and `A^H b`.
    fn normal_equations(&self) -> (Vec<Cx>, Vec<Cx>) {
        let n = self.ncol;
        let mut h = vec![Cx::ZERO; n * n];
        let mut g = vec![Cx::ZERO; n];
        for row in &self.rows {
            for &(p, cp) in &row.cols {
                let cpc = cp.conj();
                for &(q, cq) in &row.cols {
                    h[p * n + q] = h[p * n + q] + cpc * cq;
                }
                g[p] = g[p] + cpc * row.rhs;
            }
        }
        (h, g)
    }

    /// `A^H (b - A x)`, the gradient of the residual at `x`, computed from the
    /// original rows rather than from the normal matrix. Computing it this way
    /// is what makes the refinement step actually recover digits.
    fn gradient_at(&self, x: &[Cx]) -> Vec<Cx> {
        let mut g = vec![Cx::ZERO; self.ncol];
        for row in &self.rows {
            let mut ax = Cx::ZERO;
            for &(p, cp) in &row.cols {
                ax = ax + cp * x[p];
            }
            let r = row.rhs - ax;
            for &(p, cp) in &row.cols {
                g[p] = g[p] + cp.conj() * r;
            }
        }
        g
    }

    fn solve(&self) -> Option<Vec<Cx>> {
        if self.ncol == 0 || self.rows.is_empty() {
            return None;
        }
        let (h, g) = self.normal_equations();
        let l = cholesky(&h, self.ncol)?;
        let mut x = cholesky_solve(&l, self.ncol, &g);
        // Two steps of iterative refinement. Normal equations square the
        // condition number; this puts most of the lost digits back for a cost
        // of two triangular solves.
        for _ in 0..2 {
            let r = self.gradient_at(&x);
            let d = cholesky_solve(&l, self.ncol, &r);
            let mut moved = false;
            for (xi, di) in x.iter_mut().zip(d.iter()) {
                if di.norm_sq() > 0.0 {
                    moved = true;
                }
                *xi = *xi + *di;
            }
            if !moved {
                break;
            }
        }
        if x.iter().all(|v| v.is_finite()) {
            Some(x)
        } else {
            None
        }
    }
}

/// Hermitian Cholesky `H = L L^H`, reading only the lower triangle of `h`.
///
/// `None` if `H` is not positive definite, which for these systems means the
/// unknowns are not all constrained. That is information, not an error.
fn cholesky(h: &[Cx], n: usize) -> Option<Vec<Cx>> {
    let mut l = vec![Cx::ZERO; n * n];
    // A relative floor on the pivot, so that a numerically-zero pivot is
    // refused rather than producing a huge spurious answer.
    let scale: f64 = (0..n).map(|p| h[p * n + p].re.abs()).fold(0.0, f64::max);
    let floor = scale * 1e-14;
    for p in 0..n {
        let mut s = h[p * n + p].re;
        for k in 0..p {
            s -= l[p * n + k].norm_sq();
        }
        if !s.is_finite() || s <= floor {
            return None;
        }
        let d = s.sqrt();
        l[p * n + p] = Cx::real(d);
        for q in p + 1..n {
            let mut t = h[q * n + p];
            for k in 0..p {
                t = t - l[q * n + k] * l[p * n + k].conj();
            }
            l[q * n + p] = t.scale(1.0 / d);
        }
    }
    Some(l)
}

/// Solve `L L^H x = g` by forward then backward substitution.
fn cholesky_solve(l: &[Cx], n: usize, g: &[Cx]) -> Vec<Cx> {
    let mut y = vec![Cx::ZERO; n];
    for p in 0..n {
        let mut s = g[p];
        for k in 0..p {
            s = s - l[p * n + k] * y[k];
        }
        y[p] = s.scale(1.0 / l[p * n + p].re);
    }
    let mut x = vec![Cx::ZERO; n];
    for p in (0..n).rev() {
        let mut s = y[p];
        for k in p + 1..n {
            s = s - l[k * n + p].conj() * x[k];
        }
        x[p] = s.scale(1.0 / l[p * n + p].re);
    }
    x
}

// ===========================================================================
// the edge graph and the global solvers
// ===========================================================================

/// One measured pairwise transform: frame `i` coordinates to frame `j`
/// coordinates, plus the statistics needed to weight it.
#[derive(Clone, Copy, Debug)]
pub struct AlignEdge {
    pub i: usize,
    pub j: usize,
    pub t: Similarity,
    /// Tile residual RMS of the fit, plane px.
    pub rms: f64,
    /// Tiles the fit rests on.
    pub used: usize,
    /// RMS tile radius, plane px — the lever arm of the scale estimate.
    pub lever: f64,
}

impl AlignEdge {
    /// Frame separation. The single most informative property of an edge: a
    /// solve whose edges are all short is a chain wearing a solver's clothes.
    pub fn span(&self) -> usize {
        self.j.abs_diff(self.i)
    }

    pub fn from_stage(i: usize, j: usize, s: &StageFit) -> Self {
        Self {
            i,
            j,
            t: s.similarity(),
            rms: s.rms as f64,
            used: s.used,
            lever: s.lever_rms as f64,
        }
    }
}

/// How an edge's least-squares weight is derived.
///
/// All three are offered, and which one is right is **not** a matter of taste:
/// M10 measured `Unit` at 6.997 plane px held-out on a deep stack where
/// `InverseVariance` scored 24.011, and measured the ordering *reversed* on
/// shallow stacks. The mechanism is that `rms` is inflated on long-span pairs
/// by the defocus asymmetry, so inverse-variance weighting quietly discards
/// exactly the long edges that break the chaining degeneracy. Choose by
/// measurement on the stack in hand.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Weighting {
    /// Every edge weighted alike.
    Unit,
    /// By tile count only.
    Count,
    /// From the fit's own statistics.
    InverseVariance,
}

impl Weighting {
    /// Per-edge standard errors `(sigma_A, sigma_B)` in plane px at the corner
    /// radius.
    ///
    /// The standard error of a least-squares translation is `rms/sqrt(used)`;
    /// of the scale term, `rms/(lever*sqrt(used))`, which becomes
    /// `rho*rms/(lever*sqrt(used))` px at the corner. The fallbacks for a
    /// missing lever or rms reproduce M10's.
    pub fn sigmas(self, e: &AlignEdge, rho: f64) -> (f64, f64) {
        match self {
            Weighting::Unit => (1.0, 1.0),
            Weighting::Count => {
                let n = e.used.max(1) as f64;
                (1.0 / n.sqrt(), 1.0 / n.sqrt())
            }
            Weighting::InverseVariance => {
                let n = e.used.max(1) as f64;
                let lever = if e.lever.is_finite() && e.lever > 1.0 {
                    e.lever
                } else {
                    1000.0
                };
                let rms = if e.rms.is_finite() && e.rms > 1e-6 {
                    e.rms
                } else {
                    0.19
                };
                (rho * rms / (lever * n.sqrt()), rms / n.sqrt())
            }
        }
    }
}

/// Options for [`solve_global`].
#[derive(Clone, Debug)]
pub struct GlobalOptions {
    pub weighting: Weighting,
    /// IRLS passes. 1 disables robust re-weighting.
    pub irls_iters: usize,
    /// Huber threshold, plane px of corner error.
    pub huber_px: f64,
    /// Weight on a second-difference prior in frame index. Zero disables it.
    ///
    /// The prior encodes the *physics*: focus breathing is monotone and smooth
    /// in focus position, so the transform should be smooth in frame index. It
    /// also makes the system full rank across frames no edge reaches, which is
    /// why coverage is reported unconditionally when it is on.
    pub smooth: f64,
    pub geometry: PlaneGeometry,
}

impl GlobalOptions {
    pub fn new(geometry: PlaneGeometry) -> Self {
        Self {
            weighting: Weighting::Unit,
            irls_iters: 3,
            huber_px: 3.0,
            smooth: 0.0,
            geometry,
        }
    }
}

/// A per-frame transform relative to frame 0, or `None` where nothing
/// constrains it.
pub type Placement = Vec<Option<Similarity>>;

/// Connectivity and cycle structure of an edge set.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct GraphStats {
    pub n_frames: usize,
    /// Distinct `(i, j)` pairs.
    pub n_edges: usize,
    pub components: usize,
    /// `n_edges - (n_frames - components)`. Zero means the graph is a forest.
    pub cycle_rank: usize,
    pub reachable_from_0: usize,
    pub is_tree: bool,
}

/// Cycle rank and connectivity of an edge set.
///
/// Report this **before** believing any global solve. A bundle adjustment over
/// a graph with no cycles is algebraically identical to chaining along that
/// graph: there is nothing for the least squares to reconcile. A design whose
/// training graph is a tree is structurally incapable of distinguishing the two
/// and its result says nothing about whether global solving beats chaining.
pub fn graph_stats(edges: &[AlignEdge], n: usize) -> GraphStats {
    let mut parent: Vec<usize> = (0..n).collect();
    fn find(parent: &mut [usize], mut x: usize) -> usize {
        while parent[x] != x {
            parent[x] = parent[parent[x]];
            x = parent[x];
        }
        x
    }
    let uniq = unique_pairs(edges);
    for &(i, j) in &uniq {
        let (ri, rj) = (find(&mut parent, i), find(&mut parent, j));
        if ri != rj {
            parent[ri] = rj;
        }
    }
    let mut roots: Vec<usize> = (0..n).map(|k| find(&mut parent, k)).collect();
    let root0 = if n > 0 { roots[0] } else { 0 };
    let reachable = roots.iter().filter(|r| **r == root0).count();
    roots.sort_unstable();
    roots.dedup();
    let components = roots.len();
    let tree_edges = n.saturating_sub(components);
    GraphStats {
        n_frames: n,
        n_edges: uniq.len(),
        components,
        cycle_rank: uniq.len().saturating_sub(tree_edges),
        reachable_from_0: reachable,
        is_tree: uniq.len() == tree_edges,
    }
}

fn unique_pairs(edges: &[AlignEdge]) -> Vec<(usize, usize)> {
    let mut v: Vec<(usize, usize)> = edges.iter().map(|e| (e.i, e.j)).collect();
    v.sort_unstable();
    v.dedup();
    v
}

/// Frames connected to frame 0 through the measured edge graph.
///
/// Frames outside that component are constrained by no edge relative to the
/// anchor. They must be reported as *not covered*, never as a number.
pub fn reachable_from_zero(edges: &[AlignEdge], n: usize) -> Vec<bool> {
    let mut adj: Vec<Vec<usize>> = vec![Vec::new(); n];
    for e in edges {
        if e.i < n && e.j < n {
            adj[e.i].push(e.j);
            adj[e.j].push(e.i);
        }
    }
    let mut seen = vec![false; n];
    if n == 0 {
        return seen;
    }
    seen[0] = true;
    let mut stack = vec![0usize];
    while let Some(k) = stack.pop() {
        for &m in &adj[k] {
            if !seen[m] {
                seen[m] = true;
                stack.push(m);
            }
        }
    }
    seen
}

/// Deduplicate edges by `(i, j)`, preferring the fit resting on more tiles.
fn edge_map(edges: &[AlignEdge]) -> Vec<AlignEdge> {
    let mut keyed: Vec<AlignEdge> = Vec::new();
    let mut index: std::collections::HashMap<(usize, usize), usize> =
        std::collections::HashMap::new();
    for e in edges {
        match index.get(&(e.i, e.j)) {
            Some(&k) => {
                if e.used > keyed[k].used {
                    keyed[k] = *e;
                }
            }
            None => {
                index.insert((e.i, e.j), keyed.len());
                keyed.push(*e);
            }
        }
    }
    keyed
}

/// `S0` — the status quo: every frame placed by its **direct** fit to frame 0.
///
/// This is what `AGENTS.md` rule 6 recommends as the safe default, and it is
/// unbiased by construction because nothing is composed. Its weakness is
/// coverage, not accuracy: on a deep bracket the frames furthest from the
/// anchor are too defocused relative to it to correlate at all, and this
/// returns `None` for them rather than guessing.
pub fn solve_fixed(edges: &[AlignEdge], n: usize) -> Placement {
    let m = edge_map(edges);
    let mut g: Placement = vec![None; n];
    if n == 0 {
        return g;
    }
    g[0] = Some(Similarity::IDENTITY);
    for e in &m {
        if e.i == 0 && e.j < n {
            g[e.j] = Some(e.t);
        }
    }
    g
}

/// `S1`/`S2` — minimum-hop composition over edges of span at most `max_span`.
///
/// **`max_span = 1` is the adjacent chain that `AGENTS.md` rule 6 forbids.** It
/// is implemented here only so that the forbidden thing can be *measured*
/// rather than asserted; M10 measured it at 40.342 plane px held-out against
/// the global solve's 6.758. Do not ship it.
///
/// Returns the placements and the hop count each frame needed.
pub fn solve_hops(edges: &[AlignEdge], n: usize, max_span: usize) -> (Placement, Vec<usize>) {
    let m = edge_map(edges);
    let mut adj: Vec<Vec<(usize, usize, Similarity)>> = vec![Vec::new(); n];
    for e in &m {
        if e.span() > max_span || e.i >= n || e.j >= n {
            continue;
        }
        adj[e.i].push((e.j, e.span(), e.t));
        if let Some(inv) = e.t.invert() {
            adj[e.j].push((e.i, e.span(), inv));
        }
    }
    // Among equal-hop arrivals prefer the longest available span, then the
    // lowest neighbour index — a deterministic tie-break, so that the result
    // does not depend on edge insertion order.
    for a in adj.iter_mut() {
        a.sort_by(|x, y| y.1.cmp(&x.1).then(x.0.cmp(&y.0)));
    }

    let mut g: Placement = vec![None; n];
    let mut hops = vec![0usize; n];
    if n == 0 {
        return (g, hops);
    }
    g[0] = Some(Similarity::IDENTITY);
    let mut seen = vec![false; n];
    seen[0] = true;
    let mut q = VecDeque::from([0usize]);
    while let Some(u) = q.pop_front() {
        let gu = match g[u] {
            Some(t) => t,
            None => continue,
        };
        for &(v, _s, t) in &adj[u] {
            if seen[v] {
                continue;
            }
            seen[v] = true;
            g[v] = Some(gu.then(t));
            hops[v] = hops[u] + 1;
            q.push_back(v);
        }
    }
    (g, hops)
}

/// Substitute the gauge `A_0 = 1` (or `B_0 = 0`) into one row coefficient.
///
/// `gauge` is the fixed value of the frame-0 unknown for this block.
fn push_coeff(
    cols: &mut Vec<(usize, Cx)>,
    rhs: &mut Cx,
    col_of: &[Option<usize>],
    frame: usize,
    coeff: Cx,
    gauge: Cx,
) -> bool {
    if frame == 0 {
        *rhs = *rhs - coeff * gauge;
        return true;
    }
    match col_of.get(frame).copied().flatten() {
        Some(c) => {
            cols.push((c, coeff));
            true
        }
        None => false,
    }
}

/// `S3`/`S6` — global bundle adjustment over every measured edge at once.
///
/// One weighted complex linear least squares in the unknowns
/// `[A_1..A_{n-1}, B_1..B_{n-1}]`, with the gauge `A_0 = 1, B_0 = 0`. Each edge
/// contributes two rows,
///
/// ```text
/// A_j = a_ij * A_i          B_j = a_ij * B_i + b_ij
/// ```
///
/// both divided by that edge's own standard error so the system is in units of
/// plane px at the corner.
///
/// The system is **exactly block diagonal**: the first constraint involves only
/// `A` unknowns and the second only `B` unknowns. So this solves two
/// independent `n-1` systems rather than one `2(n-1)` system, which is a factor
/// of eight in the factorisation and is not an approximation. The blocks couple
/// only through the IRLS weights, which are computed from the joint corner
/// error, so both are re-solved every pass.
///
/// With `smooth = 0` the answer is `None` for every frame outside frame 0's
/// connected component. With `smooth > 0` the prior itself links every frame,
/// so all frames are placed — and the placement of an edge-less frame is then
/// an *extrapolation of the model*, not a measurement. Say so when reporting.
pub fn solve_global(edges: &[AlignEdge], n: usize, opts: &GlobalOptions) -> Option<Placement> {
    if n == 0 {
        return None;
    }
    let rho = corner_radius(opts.geometry);
    let reach = reachable_from_zero(edges, n);
    let use_all = opts.smooth > 0.0;

    // Column layout for one block: frame 0 is the gauge and has no column.
    let mut col_of: Vec<Option<usize>> = vec![None; n];
    let mut ncol = 0usize;
    for (k, c) in col_of.iter_mut().enumerate().skip(1) {
        if use_all || reach[k] {
            *c = Some(ncol);
            ncol += 1;
        }
    }
    if ncol == 0 {
        let mut g: Placement = vec![None; n];
        g[0] = Some(Similarity::IDENTITY);
        return Some(g);
    }

    let mut weights: std::collections::HashMap<(usize, usize), f64> =
        std::collections::HashMap::new();
    let mut placement: Placement = vec![None; n];
    let passes = opts.irls_iters.max(1);

    for pass in 0..passes {
        let mut sys_a = LeastSquares::new(ncol);
        let mut sys_b = LeastSquares::new(ncol);

        for e in edges {
            if e.i >= n || e.j >= n {
                continue;
            }
            let extra = weights.get(&(e.i, e.j)).copied().unwrap_or(1.0);
            if extra <= 0.0 {
                continue;
            }
            let (sa, sb) = opts.weighting.sigmas(e, rho);
            let wa = extra.sqrt() * rho / sa.max(1e-9);
            let wb = extra.sqrt() / sb.max(1e-9);

            let mut cols = Vec::with_capacity(2);
            let mut rhs = Cx::ZERO;
            let ok = push_coeff(&mut cols, &mut rhs, &col_of, e.i, e.t.a, Cx::ONE)
                && push_coeff(&mut cols, &mut rhs, &col_of, e.j, -Cx::ONE, Cx::ONE);
            if ok && !cols.is_empty() {
                sys_a.push(
                    cols.into_iter().map(|(c, v)| (c, v.scale(wa))).collect(),
                    rhs.scale(wa),
                );
            }

            let mut cols = Vec::with_capacity(2);
            let mut rhs = -e.t.b;
            let ok = push_coeff(&mut cols, &mut rhs, &col_of, e.i, e.t.a, Cx::ZERO)
                && push_coeff(&mut cols, &mut rhs, &col_of, e.j, -Cx::ONE, Cx::ZERO);
            if ok && !cols.is_empty() {
                sys_b.push(
                    cols.into_iter().map(|(c, v)| (c, v.scale(wb))).collect(),
                    rhs.scale(wb),
                );
            }
        }

        if opts.smooth > 0.0 && n >= 3 {
            for k in 1..n - 1 {
                let stencil = [(k - 1, 1.0), (k, -2.0), (k + 1, 1.0)];
                let mut cols = Vec::with_capacity(3);
                let mut rhs = Cx::ZERO;
                for (kk, c) in stencil {
                    push_coeff(&mut cols, &mut rhs, &col_of, kk, Cx::real(c), Cx::ONE);
                }
                let w = opts.smooth * rho;
                sys_a.push(
                    cols.into_iter().map(|(c, v)| (c, v.scale(w))).collect(),
                    rhs.scale(w),
                );

                let mut cols = Vec::with_capacity(3);
                let mut rhs = Cx::ZERO;
                for (kk, c) in stencil {
                    push_coeff(&mut cols, &mut rhs, &col_of, kk, Cx::real(c), Cx::ZERO);
                }
                let w = opts.smooth;
                sys_b.push(
                    cols.into_iter().map(|(c, v)| (c, v.scale(w))).collect(),
                    rhs.scale(w),
                );
            }
        }

        let xa = sys_a.solve()?;
        let xb = sys_b.solve()?;

        placement = vec![None; n];
        placement[0] = Some(Similarity::IDENTITY);
        for (k, c) in col_of.iter().enumerate() {
            if let Some(c) = c {
                placement[k] = Some(Similarity {
                    a: xa[*c],
                    b: xb[*c],
                });
            }
        }

        if pass + 1 == passes {
            break;
        }
        weights.clear();
        for e in edges {
            let (Some(gi), Some(gj)) = (
                placement.get(e.i).copied().flatten(),
                placement.get(e.j).copied().flatten(),
            ) else {
                continue;
            };
            let Some(pred) = Similarity::relative(gi, gj) else {
                continue;
            };
            let r = pred.corner_err(e.t, opts.geometry);
            let w = if r <= opts.huber_px {
                1.0
            } else {
                opts.huber_px / r
            };
            weights.insert((e.i, e.j), w);
        }
    }

    Some(placement)
}

// ===========================================================================
// the parametric solver: transform as a smooth function of frame index
// ===========================================================================

/// How the translation is modelled once the scale track is fixed.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum TranslationModel {
    /// One free complex unknown per frame. The weakest parametric claim, and
    /// the one that cannot be wrong about translation.
    Free,
    /// A complex polynomial of this degree in normalised frame index, with
    /// `B_0 = 0`.
    Poly(usize),
    /// `B_j = (1 - A_j) * c` for a single complex centre `c`: pure
    /// magnification about a fixed point.
    ///
    /// This is the **strongest** claim the model can make and the most useful
    /// one if it holds, because it reduces a whole bracket's geometry to one
    /// scale track plus two numbers. It is also the one most likely to be
    /// falsified: M10 measured the fitted centre moving by 150 plane px between
    /// two configurations on the same stack, and by hundreds of px between
    /// stacks on the same rig. Treat a fitted centre as a per-stack nuisance
    /// parameter, never as an optics constant.
    FixedCentre,
}

/// Options for [`solve_poly`].
#[derive(Clone, Debug)]
pub struct PolyOptions {
    /// Degree of the complex polynomial in `log A`.
    pub degree: usize,
    pub translation: TranslationModel,
    pub weighting: Weighting,
    pub irls_iters: usize,
    pub huber_px: f64,
    pub geometry: PlaneGeometry,
}

impl PolyOptions {
    pub fn new(geometry: PlaneGeometry) -> Self {
        Self {
            degree: 6,
            translation: TranslationModel::Free,
            weighting: Weighting::Unit,
            irls_iters: 3,
            huber_px: 3.0,
            geometry,
        }
    }
}

/// The result of a parametric solve.
#[derive(Clone, Debug)]
pub struct PolySolution {
    pub transforms: Placement,
    /// Coefficients of `log A` in the basis `t, t^2, ... t^degree`.
    pub log_scale_coeffs: Vec<Cx>,
    /// The fitted centre of expansion, when [`TranslationModel::FixedCentre`]
    /// was used. Plane px relative to the plane centre.
    pub centre: Option<Cx>,
}

/// Basis with no constant term, so `P(0) = 0` by construction.
fn poly_basis(j: usize, deg: usize, n: usize) -> Vec<f64> {
    let t = j as f64 / (n.saturating_sub(1)).max(1) as f64;
    (1..=deg).map(|k| t.powi(k as i32)).collect()
}

/// `S4`/`S5` — model the transform as a smooth function of frame index.
///
/// `log A_j = P(j)` for a complex polynomial `P` with `P(0) = 0`, fitted
/// directly to the edge constraints `log a_ij = P(j) - P(i)`.
///
/// This is the structural advantage a deep stack hands you. Focus breathing is
/// a smooth, near-monotone function of focus position, and focus position is a
/// smooth function of frame index in a bracket. A degree-6 polynomial across
/// 299 frames has seven complex unknowns against hundreds of measurements,
/// where a free solve has 298; the parametric fit is therefore far better
/// conditioned and averages down the per-edge estimation error instead of
/// absorbing it.
///
/// It also gives a *diagnostic that a free solve cannot*: if the residual of
/// the parametric fit is smooth in frame index, what is left over is real
/// geometry the model is missing; if it is noisy, it is estimation error and
/// no richer geometric model will help.
///
/// The `log` is safe: `|a - 1|` stays under a tenth over a whole bracket, so
/// the principal branch is unambiguous and no unwrapping is needed.
pub fn solve_poly(edges: &[AlignEdge], n: usize, opts: &PolyOptions) -> Option<PolySolution> {
    if n == 0 || opts.degree == 0 {
        return None;
    }
    let rho = corner_radius(opts.geometry);
    let deg = opts.degree;
    let mut weights: std::collections::HashMap<(usize, usize), f64> =
        std::collections::HashMap::new();
    let mut coef: Vec<Cx> = Vec::new();
    let passes = opts.irls_iters.max(1);

    for pass in 0..passes {
        let mut sys = LeastSquares::new(deg);
        for e in edges {
            if e.i >= n || e.j >= n {
                continue;
            }
            let extra = weights.get(&(e.i, e.j)).copied().unwrap_or(1.0);
            if extra <= 0.0 {
                continue;
            }
            let (sa, _) = opts.weighting.sigmas(e, rho);
            let wa = extra.sqrt() * rho / sa.max(1e-9);
            let bi = poly_basis(e.i, deg, n);
            let bj = poly_basis(e.j, deg, n);
            let cols: Vec<(usize, Cx)> = (0..deg)
                .map(|k| (k, Cx::real((bj[k] - bi[k]) * wa)))
                .collect();
            sys.push(cols, e.t.a.ln().scale(wa));
        }
        coef = sys.solve()?;
        if pass + 1 == passes {
            break;
        }
        let scales = poly_scales(&coef, n, deg);
        weights.clear();
        for e in edges {
            if e.i >= n || e.j >= n {
                continue;
            }
            let r = rho * (e.t.a * scales[e.i] - scales[e.j]).abs();
            let w = if r <= opts.huber_px {
                1.0
            } else {
                opts.huber_px / r
            };
            weights.insert((e.i, e.j), w);
        }
    }

    let scales = poly_scales(&coef, n, deg);

    // The translation half is solved once, with the sigma weights only. It gets
    // no Huber weights: those were fitted to the *scale* residual and applying
    // them here would down-weight edges for a reason that has nothing to do
    // with their translation.
    let translations = match opts.translation {
        TranslationModel::FixedCentre => {
            let mut sys = LeastSquares::new(1);
            for e in edges {
                if e.i >= n || e.j >= n {
                    continue;
                }
                let (_, sb) = opts.weighting.sigmas(e, rho);
                let wb = 1.0 / sb.max(1e-9);
                let c = (e.t.a * (Cx::ONE - scales[e.i]) - (Cx::ONE - scales[e.j])).scale(wb);
                sys.push(vec![(0, c)], (-e.t.b).scale(wb));
            }
            let x = sys.solve()?;
            let c = x[0];
            return Some(PolySolution {
                transforms: (0..n)
                    .map(|j| {
                        Some(Similarity {
                            a: scales[j],
                            b: (Cx::ONE - scales[j]) * c,
                        })
                    })
                    .collect(),
                log_scale_coeffs: coef,
                centre: Some(c),
            });
        }
        TranslationModel::Poly(bdeg) => {
            if bdeg == 0 {
                return None;
            }
            let mut sys = LeastSquares::new(bdeg);
            for e in edges {
                if e.i >= n || e.j >= n {
                    continue;
                }
                let (_, sb) = opts.weighting.sigmas(e, rho);
                let wb = 1.0 / sb.max(1e-9);
                let bi = poly_basis(e.i, bdeg, n);
                let bj = poly_basis(e.j, bdeg, n);
                let cols: Vec<(usize, Cx)> = (0..bdeg)
                    .map(|k| (k, (e.t.a.scale(bi[k]) - Cx::real(bj[k])).scale(wb)))
                    .collect();
                sys.push(cols, (-e.t.b).scale(wb));
            }
            let x = sys.solve()?;
            let mut b: Vec<Option<Cx>> = (0..n)
                .map(|j| {
                    let basis = poly_basis(j, bdeg, n);
                    Some(
                        basis
                            .iter()
                            .zip(x.iter())
                            .fold(Cx::ZERO, |acc, (bk, xk)| acc + xk.scale(*bk)),
                    )
                })
                .collect();
            b[0] = Some(Cx::ZERO);
            b
        }
        TranslationModel::Free => {
            let reach = reachable_from_zero(edges, n);
            let mut col_of: Vec<Option<usize>> = vec![None; n];
            let mut ncol = 0usize;
            for (k, c) in col_of.iter_mut().enumerate().skip(1) {
                if reach[k] {
                    *c = Some(ncol);
                    ncol += 1;
                }
            }
            if ncol == 0 {
                let mut b: Vec<Option<Cx>> = vec![None; n];
                b[0] = Some(Cx::ZERO);
                b
            } else {
                let mut sys = LeastSquares::new(ncol);
                for e in edges {
                    if e.i >= n || e.j >= n {
                        continue;
                    }
                    let (_, sb) = opts.weighting.sigmas(e, rho);
                    let wb = 1.0 / sb.max(1e-9);
                    let mut cols = Vec::with_capacity(2);
                    let mut rhs = -e.t.b;
                    let ok = push_coeff(&mut cols, &mut rhs, &col_of, e.i, e.t.a, Cx::ZERO)
                        && push_coeff(&mut cols, &mut rhs, &col_of, e.j, -Cx::ONE, Cx::ZERO);
                    if ok && !cols.is_empty() {
                        sys.push(
                            cols.into_iter().map(|(c, v)| (c, v.scale(wb))).collect(),
                            rhs.scale(wb),
                        );
                    }
                }
                let x = sys.solve()?;
                let mut b: Vec<Option<Cx>> = vec![None; n];
                b[0] = Some(Cx::ZERO);
                for (k, c) in col_of.iter().enumerate() {
                    if let Some(c) = c {
                        b[k] = Some(x[*c]);
                    }
                }
                b
            }
        }
    };

    Some(PolySolution {
        transforms: translations
            .into_iter()
            .enumerate()
            .map(|(j, b)| b.map(|b| Similarity { a: scales[j], b }))
            .collect(),
        log_scale_coeffs: coef,
        centre: None,
    })
}

fn poly_scales(coef: &[Cx], n: usize, deg: usize) -> Vec<Cx> {
    let mut out: Vec<Cx> = (0..n)
        .map(|j| {
            let basis = poly_basis(j, deg, n);
            basis
                .iter()
                .zip(coef.iter())
                .fold(Cx::ZERO, |acc, (bk, ck)| acc + ck.scale(*bk))
                .exp()
        })
        .collect();
    if !out.is_empty() {
        out[0] = Cx::ONE;
    }
    out
}

// ===========================================================================
// metrics
// ===========================================================================

/// The transform a placement predicts between two frames, if both are placed.
pub fn predict(placement: &[Option<Similarity>], i: usize, j: usize) -> Option<Similarity> {
    Similarity::relative((*placement.get(i)?)?, (*placement.get(j)?)?)
}

/// How far a placement disagrees with one measured edge.
#[derive(Clone, Copy, Debug)]
pub struct EdgeError {
    pub i: usize,
    pub j: usize,
    pub span: usize,
    /// Worst-corner disagreement, plane px.
    pub err: f64,
    /// The scale/rotation part, `rho*|da|`.
    pub err_scale: f64,
    /// The translation part, `|db|`.
    pub err_trans: f64,
}

/// Corner error of every measured edge against a placement.
///
/// Computed over *held-out* edges this is the only honest accuracy figure;
/// computed over the edges the placement was fitted to it is a fit residual and
/// says nothing about accuracy. The function cannot tell which you gave it —
/// that discipline is the caller's.
pub fn edge_errors(
    placement: &[Option<Similarity>],
    edges: &[AlignEdge],
    geom: PlaneGeometry,
) -> Vec<EdgeError> {
    let mut out = Vec::with_capacity(edges.len());
    for e in edges {
        let Some(p) = predict(placement, e.i, e.j) else {
            continue;
        };
        let (s, t) = p.corner_err_parts(e.t, geom);
        out.push(EdgeError {
            i: e.i,
            j: e.j,
            span: e.span(),
            err: p.corner_err(e.t, geom),
            err_scale: s,
            err_trans: t,
        });
    }
    out
}

/// One cycle-consistency triple.
#[derive(Clone, Copy, Debug)]
pub struct CycleTriple {
    pub i: usize,
    pub j: usize,
    pub k: usize,
    pub span_ik: usize,
    /// Corner error of the direct fit `i->k` against `(i->j)` then `(j->k)`.
    pub err: f64,
    pub err_scale: f64,
    pub err_trans: f64,
}

/// Cycle consistency of the raw measurements.
///
/// For every triple `i < j < k` with all three edges measured, the corner error
/// of the direct `i->k` fit against the composition of `i->j` and `j->k`.
///
/// This is computed **from the data alone**, with no solver involved, so it
/// bounds what any solver can achieve: if the measurements disagree with
/// themselves by `x` px around a closed loop, no reconciliation of them can be
/// right to better than about `x`. Measure this before believing any global
/// solve is "converged".
///
/// Subsampling to `max_triples` is a deterministic stride, not a random draw —
/// a random subsample would make the number depend on a seed, and there is no
/// RNG in this crate's dependency set.
pub fn cycle_consistency(
    edges: &[AlignEdge],
    geom: PlaneGeometry,
    max_triples: usize,
) -> Vec<CycleTriple> {
    let m = edge_map(edges);
    let mut index: std::collections::HashMap<(usize, usize), Similarity> =
        std::collections::HashMap::new();
    let mut by_i: std::collections::HashMap<usize, Vec<usize>> = std::collections::HashMap::new();
    for e in &m {
        index.insert((e.i, e.j), e.t);
        by_i.entry(e.i).or_default().push(e.j);
    }
    for v in by_i.values_mut() {
        v.sort_unstable();
    }

    let mut trip: Vec<(usize, usize, usize)> = Vec::new();
    let mut keys: Vec<(usize, usize)> = index.keys().copied().collect();
    keys.sort_unstable();
    for (i, k) in keys {
        let Some(js) = by_i.get(&i) else { continue };
        for &j in js {
            if i < j && j < k && index.contains_key(&(j, k)) {
                trip.push((i, j, k));
            }
        }
    }
    let stride = if max_triples == 0 || trip.len() <= max_triples {
        1
    } else {
        trip.len().div_ceil(max_triples)
    };

    trip.into_iter()
        .step_by(stride)
        .filter_map(|(i, j, k)| {
            let direct = *index.get(&(i, k))?;
            let chained = index.get(&(i, j))?.then(*index.get(&(j, k))?);
            let (s, t) = direct.corner_err_parts(chained, geom);
            Some(CycleTriple {
                i,
                j,
                k,
                span_ik: k - i,
                err: direct.corner_err(chained, geom),
                err_scale: s,
                err_trans: t,
            })
        })
        .collect()
}

/// Total corner drift a placement carries: the largest corner error of any
/// placed frame against the identity.
///
/// **This is the number that decides whether alignment is worth doing at all.**
/// If a whole bracket drifts less than the blur it is being merged through,
/// registration is not what is making the result soft, and the honest answer is
/// to say so rather than to ship a transform.
pub fn total_drift(placement: &[Option<Similarity>], geom: PlaneGeometry) -> f64 {
    placement
        .iter()
        .flatten()
        .map(|t| t.corner_err(Similarity::IDENTITY, geom))
        .fold(0.0f64, f64::max)
}

// ===========================================================================
// gather-time resampling
// ===========================================================================

/// Point sample with no interpolation at all.
///
/// Present because it is the **control**, not because it is a resampler: every
/// interpolator is a lowpass, so an experiment that measures a transform by
/// warping an image has an instrument effect baked into it. M23 measured a
/// zero-defocus self-pair reading 0.372 through a bilinear resample where the
/// truth is 1.000 by construction, and 0.9645 point-sampled. Any planted-warp
/// control must be plantable without interpolation, or its own answer is what
/// is being measured.
#[inline]
pub fn sample_nearest(p: PlaneRef<'_>, x: f64, y: f64) -> f32 {
    let xi = (x.round() as isize).clamp(0, p.width as isize - 1) as usize;
    let yi = (y.round() as isize).clamp(0, p.height as isize - 1) as usize;
    p.data[yi * p.width + xi]
}

/// Bilinear gather. Cheap, and measurably soft.
#[inline]
pub fn sample_bilinear(p: PlaneRef<'_>, x: f64, y: f64) -> f32 {
    if p.width < 2 || p.height < 2 {
        return sample_nearest(p, x, y);
    }
    let x = x.clamp(0.0, (p.width - 2) as f64);
    let y = y.clamp(0.0, (p.height - 2) as f64);
    let (x0, y0) = (x.floor() as usize, y.floor() as usize);
    let (fx, fy) = ((x - x0 as f64) as f32, (y - y0 as f64) as f32);
    let i = y0 * p.width + x0;
    let a = p.data[i] * (1.0 - fx) + p.data[i + 1] * fx;
    let b = p.data[i + p.width] * (1.0 - fx) + p.data[i + p.width + 1] * fx;
    a * (1.0 - fy) + b * fy
}

/// Catmull-Rom weights for the four taps at offsets `-1, 0, 1, 2`.
#[inline]
fn catmull_rom_weights(f: f32) -> [f32; 4] {
    let f2 = f * f;
    let f3 = f2 * f;
    [
        -0.5 * f3 + f2 - 0.5 * f,
        1.5 * f3 - 2.5 * f2 + 1.0,
        -1.5 * f3 + 2.0 * f2 + 0.5 * f,
        0.5 * f3 - 0.5 * f2,
    ]
}

/// Catmull-Rom (cubic, `a = -1/2`) gather.
///
/// The default for the merge's gather step. It is interpolating — it reproduces
/// the sample values exactly at integer positions, so an identity transform is
/// a true identity — and its passband is far flatter than bilinear's, which is
/// the whole point when the pipeline exists to preserve fine detail. It does
/// overshoot at hard edges; on linear sensor data that shows up as a small
/// negative excursion beside a specular highlight, which is why the caller
/// should clamp at zero when the result feeds anything that indexes a noise
/// model.
///
/// Do not read the choice as free: measure the round-trip cost on the stack in
/// hand. Two resamples is one too many.
pub fn sample_catmull_rom(p: PlaneRef<'_>, x: f64, y: f64) -> f32 {
    if p.width < 4 || p.height < 4 {
        return sample_bilinear(p, x, y);
    }
    let x = x.clamp(1.0, (p.width - 3) as f64);
    let y = y.clamp(1.0, (p.height - 3) as f64);
    let (x0, y0) = (x.floor() as usize, y.floor() as usize);
    let wx = catmull_rom_weights((x - x0 as f64) as f32);
    let wy = catmull_rom_weights((y - y0 as f64) as f32);
    let mut acc = 0f32;
    for (dy, wyv) in wy.iter().enumerate() {
        let row = (y0 + dy - 1) * p.width + x0 - 1;
        let mut r = 0f32;
        for (dx, wxv) in wx.iter().enumerate() {
            r += p.data[row + dx] * *wxv;
        }
        acc += r * *wyv;
    }
    acc
}

/// Which interpolator a gather uses.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Resampler {
    Nearest,
    Bilinear,
    CatmullRom,
}

impl Resampler {
    #[inline]
    pub fn sample(self, p: PlaneRef<'_>, x: f64, y: f64) -> f32 {
        match self {
            Resampler::Nearest => sample_nearest(p, x, y),
            Resampler::Bilinear => sample_bilinear(p, x, y),
            Resampler::CatmullRom => sample_catmull_rom(p, x, y),
        }
    }

    /// Half-width of the interpolator's support, in plane px.
    #[inline]
    pub fn support(self) -> f64 {
        match self {
            Resampler::Nearest => 0.5,
            Resampler::Bilinear => 1.0,
            Resampler::CatmullRom => 2.0,
        }
    }

    /// [`Resampler::sample`], but `None` where the interpolator's support would
    /// leave the plane instead of clamping to the edge.
    ///
    /// **The merge must use this, not [`Resampler::sample`].** Once frames are
    /// at different scales they no longer cover the same field: the outermost
    /// ring of the largest-magnification frame has no counterpart in the
    /// smallest, and clamping there smears the border pixel inward. A merge
    /// that silently clamps produces a plausible-looking edge artefact that
    /// grows with stack depth; one that treats the sample as missing produces a
    /// slightly smaller valid rectangle, which is correct and visible.
    #[inline]
    pub fn sample_checked(self, p: PlaneRef<'_>, x: f64, y: f64) -> Option<f32> {
        let s = self.support();
        if x < s - 0.5 || y < s - 0.5 {
            return None;
        }
        if x > p.width as f64 - 0.5 - s || y > p.height as f64 - 0.5 - s {
            return None;
        }
        Some(self.sample(p, x, y))
    }
}

/// Gather frame `src` into the reference frame's grid under transform `t`.
///
/// `t` maps **reference** coordinates to **source** coordinates, so this is a
/// pull, and no forward scatter or hole filling is ever needed. Provided for
/// controls and for the example binary; the merge must call
/// [`Resampler::sample`] itself, one pixel at a time, at the point it consumes
/// a frame — materialising a warped copy of 299 frames is exactly what
/// `AGENTS.md` rule 2 forbids.
pub fn gather_into(
    src: PlaneRef<'_>,
    t: Similarity,
    geom: PlaneGeometry,
    resampler: Resampler,
    dst: &mut [f32],
) {
    assert_eq!(dst.len(), geom.pixels(), "destination is not plane-sized");
    let (cx, cy) = (geom.width as f64 * 0.5, geom.height as f64 * 0.5);
    for py in 0..geom.height {
        let row = &mut dst[py * geom.width..(py + 1) * geom.width];
        for (px, o) in row.iter_mut().enumerate() {
            let (sx, sy) = t.apply_at(px as f64, py as f64, cx, cy);
            *o = resampler.sample(src, sx, sy);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const TEST_W: usize = 400;
    const TEST_H: usize = 300;

    /// The small plane the image-domain tests run on, chosen so the estimator
    /// tests stay fast.
    fn test_geom() -> PlaneGeometry {
        PlaneGeometry {
            width: TEST_W,
            height: TEST_H,
        }
    }

    /// The **real** CFA plane of the reference rig: 7032x4688 active area,
    /// halved. Every solver and algebra test uses this, so that the plane px
    /// figures they assert are directly comparable to the ones M10 and M86
    /// report rather than being scaled by an arbitrary test geometry.
    fn plane_geom() -> PlaneGeometry {
        PlaneGeometry::from_active(7032, 4688)
    }

    /// Deterministic 32-bit LCG. No RNG dependency exists in this crate and a
    /// test that depends on one is a test that changes when the dependency
    /// does.
    struct Lcg(u64);

    impl Lcg {
        fn next_unit(&mut self) -> f32 {
            self.0 = self
                .0
                .wrapping_mul(6364136223846793005)
                .wrapping_add(1442695040888963407);
            ((self.0 >> 33) as u32 as f32) / (u32::MAX >> 1) as f32
        }
    }

    /// Broadband but band-limited texture: white noise smoothed twice, so that
    /// resampling it is meaningful rather than pure aliasing.
    fn texture(w: usize, h: usize, seed: u64) -> Vec<f32> {
        let mut rng = Lcg(seed);
        let mut v: Vec<f32> = (0..w * h)
            .map(|_| 400.0 + 600.0 * rng.next_unit())
            .collect();
        for _ in 0..2 {
            let src = v.clone();
            for y in 1..h - 1 {
                for x in 1..w - 1 {
                    let mut s = 0f32;
                    for dy in 0..3 {
                        for dx in 0..3 {
                            s += src[(y + dy - 1) * w + x + dx - 1];
                        }
                    }
                    v[y * w + x] = s / 9.0;
                }
            }
        }
        v
    }

    fn test_cfg() -> AlignConfig {
        AlignConfig {
            coarse_factors: vec![4],
            coarse_tile: 16,
            coarse_grid: (6, 4),
            coarse_radius: 6,
            fine_tile: 64,
            fine_grid: (6, 4),
            fine_radius: 5,
            margin: 24,
            ..AlignConfig::shallow()
        }
    }

    // ---- algebra -------------------------------------------------------

    #[test]
    fn complex_log_and_exp_invert_each_other_near_unity() {
        for (re, im) in [(1.0, 0.0), (1.046, 0.0031), (0.97, -0.004)] {
            let z = Cx::new(re, im);
            let back = z.ln().exp();
            assert!(
                (back - z).abs() < 1e-12,
                "ln/exp round trip failed for {z:?} -> {back:?}"
            );
        }
    }

    #[test]
    fn similarity_compose_and_invert_round_trip() {
        let geom = plane_geom();
        let t = Similarity::from_params(SimilarityParams {
            ax: 13.5,
            ay: -7.25,
            g: 0.031,
            rot: 0.0017,
        });
        let round = t.then(t.invert().expect("invertible"));
        assert!(round.corner_err(Similarity::IDENTITY, geom) < 1e-9);

        // relative(g_i, g_j) really is the i -> j transform.
        let gi = Similarity::from_params(SimilarityParams {
            ax: 3.0,
            ay: 1.0,
            g: 0.01,
            rot: 0.0002,
        });
        let gj = Similarity::from_params(SimilarityParams {
            ax: -9.0,
            ay: 4.0,
            g: 0.043,
            rot: -0.0009,
        });
        let rel = Similarity::relative(gi, gj).expect("relative");
        assert!(gi.then(rel).corner_err(gj, geom) < 1e-9);
    }

    #[test]
    fn similarity_rms_identity_holds() {
        // mean_corners |da*p + db|^2 == rho^2 |da|^2 + |db|^2, exactly, because
        // the corner set is symmetric about the plane centre. The whole
        // least-squares weighting rests on this, so it is checked rather than
        // asserted in prose.
        let geom = plane_geom();
        let rho = corner_radius(geom);
        let t1 = Similarity {
            a: Cx::new(1.021, 0.0013),
            b: Cx::new(4.0, -11.0),
        };
        let t2 = Similarity {
            a: Cx::new(1.004, -0.0007),
            b: Cx::new(-2.0, 3.5),
        };
        let lhs = t1.corner_err_rms(t2, geom).powi(2);
        let da = t1.a - t2.a;
        let db = t1.b - t2.b;
        let rhs = rho * rho * da.norm_sq() + db.norm_sq();
        assert!(
            (lhs - rhs).abs() < 1e-6 * rhs,
            "rms identity broken: {lhs} vs {rhs}"
        );
    }

    #[test]
    fn the_linearised_inverse_is_wrong_by_g_squared_rho() {
        // The trap this module exists to avoid. Warping by `p - d(p)` instead
        // of `(p - b)/a` plants an error of g^2*rho/(1+g) at the corner. At the
        // 4.6% drift M10 measured over 105 frames, on the real plane, that is
        // over four plane px -- the same size as the effect being measured. The
        // test asserts the interesting case actually occurs, i.e. that the
        // error is large, not small.
        let geom = plane_geom();
        let rho = corner_radius(geom);
        let g = 0.046;
        let t = Similarity::from_params(SimilarityParams {
            ax: 0.0,
            ay: 0.0,
            g,
            rot: 0.0,
        });
        let inv = t.invert().expect("invertible");
        let linearised = Similarity::from_params(SimilarityParams {
            ax: 0.0,
            ay: 0.0,
            g: -g,
            rot: 0.0,
        });
        let planted = inv.corner_err(linearised, geom);
        let predicted = g * g * rho / (1.0 + g);
        assert!(
            (planted - predicted).abs() < 1e-9 * rho,
            "planted {planted} vs predicted {predicted}"
        );
        assert!(
            planted > 4.0,
            "the control is uninteresting if the linearisation error is small: {planted} px"
        );
    }

    // ---- estimator -----------------------------------------------------

    #[test]
    fn tile_grid_insets_by_the_margin_and_spans_the_rest() {
        let data = vec![0f32; TEST_W * TEST_H];
        let p = PlaneRef::new(&data, TEST_W, TEST_H).expect("view");
        let spots = tile_grid(p, 64, 6, 4, 24).expect("grid");
        assert_eq!(spots.len(), 24);
        assert_eq!(spots[0], (24, 24));
        assert_eq!(spots[5].0, TEST_W - 64 - 24);
        assert_eq!(spots[23], (TEST_W - 64 - 24, TEST_H - 64 - 24));
        // A margin that leaves no room is refused rather than clamped.
        assert!(tile_grid(p, 64, 6, 4, 200).is_none());
    }

    #[test]
    fn a_featureless_tile_is_refused_rather_than_matched() {
        let flat = vec![600f32; TEST_W * TEST_H];
        let p = PlaneRef::new(&flat, TEST_W, TEST_H).expect("view");
        let cfg = test_cfg();
        let m = ncc_tile(
            p,
            p,
            TileProbe {
                tx: 100,
                ty: 100,
                size: 64,
                predicted: (0.0, 0.0),
                radius: 4,
            },
            &cfg,
        );
        assert_eq!(m.status, TileStatus::LowContrast);
        assert!(
            m.dx.is_nan(),
            "a refused tile must not carry a displacement"
        );
    }

    #[test]
    fn the_estimator_recovers_a_planted_similarity() {
        let geom = test_geom();
        let rho = corner_radius(geom);
        let cfg = test_cfg();
        let base = texture(TEST_W, TEST_H, 0x5EED_1234);
        let base_ref = PlaneRef::new(&base, TEST_W, TEST_H).expect("view");

        let truth = Similarity::from_params(SimilarityParams {
            ax: 1.75,
            ay: -2.5,
            g: 0.010,
            rot: 0.0009,
        });
        // moving(q) = reference(T^-1 q), so a pull with the inverse.
        let mut moved = vec![0f32; geom.pixels()];
        gather_into(
            base_ref,
            truth.invert().expect("invertible"),
            geom,
            Resampler::CatmullRom,
            &mut moved,
        );
        let moved_ref = PlaneRef::new(&moved, TEST_W, TEST_H).expect("view");

        let rp = AlignPyramid::build(base_ref, &cfg).expect("pyramid");
        let mp = AlignPyramid::build(moved_ref, &cfg).expect("pyramid");
        let spots = tile_grid(
            base_ref,
            cfg.fine_tile,
            cfg.fine_grid.0,
            cfg.fine_grid.1,
            cfg.margin,
        )
        .expect("grid");
        let stage = align_pair(
            AlignFrame {
                plane: base_ref,
                pyramid: &rp,
            },
            AlignFrame {
                plane: moved_ref,
                pyramid: &mp,
            },
            &spots,
            &cfg,
        )
        .expect("a self-warped pair must correlate");

        // The interesting case: the planted transform is big enough to matter.
        assert!(
            truth.corner_err(Similarity::IDENTITY, geom) > 3.0,
            "plant too small to be a test"
        );
        let err = stage.similarity().corner_err(truth, geom);
        assert!(
            err < 0.35,
            "recovered {:?} against truth {:?}: {err:.4} plane px at rho {rho:.1}",
            stage.fit,
            truth.to_params()
        );
        assert!(stage.used >= cfg.min_tiles);
        assert!(stage.rms.is_finite() && stage.rms < 1.0);
    }

    #[test]
    fn an_uncorrelatable_pair_refuses_instead_of_inventing_a_transform() {
        let cfg = test_cfg();
        let a = texture(TEST_W, TEST_H, 1);
        let b = texture(TEST_W, TEST_H, 999_983);
        let ar = PlaneRef::new(&a, TEST_W, TEST_H).expect("view");
        let br = PlaneRef::new(&b, TEST_W, TEST_H).expect("view");
        let spots = tile_grid(ar, cfg.fine_tile, 6, 4, cfg.margin).expect("grid");
        let r = fit_stage(ar, br, cfg.fine_tile, &spots, cfg.fine_radius, None, &cfg);
        // Two independent textures share no structure; the peak floor must
        // catch that. Whatever the exact reason, it must be a refusal.
        assert!(
            r.is_err(),
            "independent noise fields must not produce a fit: {r:?}"
        );
    }

    // ---- graph ---------------------------------------------------------

    fn edge(i: usize, j: usize, t: Similarity) -> AlignEdge {
        AlignEdge {
            i,
            j,
            t,
            rms: 0.2,
            used: 40,
            lever: 1200.0,
        }
    }

    /// A smooth, monotone scale track plus a fixed centre of expansion: the
    /// physical model of focus breathing.
    fn planted_track(n: usize, total_g: f64, centre: Cx) -> Vec<Similarity> {
        (0..n)
            .map(|j| {
                let t = j as f64 / (n - 1) as f64;
                // Slightly non-linear in index, as real breathing is.
                let a = Cx::new(1.0, 0.0).scale(1.0 + total_g * (0.8 * t + 0.2 * t * t))
                    + Cx::new(0.0, 0.0006 * t);
                Similarity {
                    a,
                    b: (Cx::ONE - a) * centre,
                }
            })
            .collect()
    }

    #[test]
    fn a_tree_training_graph_is_detected_as_a_tree() {
        // A bundle adjustment over a tree is chaining in disguise; a design
        // that does not check for this cannot tell the two apart.
        let t = Similarity::IDENTITY;
        let chain: Vec<AlignEdge> = (0..9).map(|k| edge(k, k + 1, t)).collect();
        let s = graph_stats(&chain, 10);
        assert!(s.is_tree);
        assert_eq!(s.cycle_rank, 0);
        assert_eq!(s.components, 1);

        let mut with_loop = chain.clone();
        with_loop.push(edge(0, 5, t));
        with_loop.push(edge(2, 9, t));
        let s2 = graph_stats(&with_loop, 10);
        assert!(!s2.is_tree);
        assert_eq!(s2.cycle_rank, 2);
    }

    #[test]
    fn a_disconnected_frame_is_reported_unplaced_not_guessed() {
        // The failure M10 hit: a minimum-norm least squares happily returns a
        // number for a frame no edge constrains, and reports full coverage.
        let t = Similarity::IDENTITY;
        let edges: Vec<AlignEdge> = (0..3).map(|k| edge(k, k + 1, t)).collect();
        let n = 6;
        let s = graph_stats(&edges, n);
        assert_eq!(s.components, 3, "frames 4 and 5 are isolated");
        assert_eq!(s.reachable_from_0, 4);

        let opts = GlobalOptions::new(plane_geom());
        let g = solve_global(&edges, n, &opts).expect("solve");
        assert!(g[3].is_some());
        assert!(g[4].is_none(), "frame 4 has no edge and must not be placed");
        assert!(g[5].is_none());
    }

    // ---- solvers -------------------------------------------------------

    #[test]
    fn the_global_solve_recovers_a_planted_track_from_noisy_edges() {
        let geom = plane_geom();
        let n = 40;
        let truth = planted_track(n, 0.045, Cx::new(-30.0, -110.0));
        let mut rng = Lcg(0xA11_6000);
        let mut edges = Vec::new();
        for span in [1usize, 4, 11] {
            for i in 0..n - span {
                let j = i + span;
                let rel = Similarity::relative(truth[i], truth[j]).expect("relative");
                // Zero-mean measurement noise, a fraction of a plane px at the
                // corner.
                let noise_a = Cx::new(
                    (rng.next_unit() as f64 - 0.5) * 4e-5,
                    (rng.next_unit() as f64 - 0.5) * 4e-5,
                );
                let noise_b = Cx::new(
                    (rng.next_unit() as f64 - 0.5) * 0.3,
                    (rng.next_unit() as f64 - 0.5) * 0.3,
                );
                edges.push(edge(
                    i,
                    j,
                    Similarity {
                        a: rel.a + noise_a,
                        b: rel.b + noise_b,
                    },
                ));
            }
        }
        let stats = graph_stats(&edges, n);
        assert!(
            stats.cycle_rank > 50,
            "the training graph must contain cycles or this proves nothing: {stats:?}"
        );

        let opts = GlobalOptions::new(geom);
        let g = solve_global(&edges, n, &opts).expect("solve");
        let worst = (0..n)
            .map(|k| g[k].expect("placed").corner_err(truth[k], geom))
            .fold(0.0f64, f64::max);
        // The plant drifts by this much in total, so the bar has to be far
        // below it to mean anything.
        let drift = truth[n - 1].corner_err(Similarity::IDENTITY, geom);
        assert!(drift > 5.0, "plant too small: {drift} px");
        assert!(worst < 0.3, "worst placement error {worst:.4} px");
    }

    #[test]
    fn chaining_compounds_a_bias_that_the_global_solve_absorbs() {
        // AGENTS.md rule 6, as a regression test rather than as a slogan. Every
        // short edge carries the same small multiplicative bias -- exactly what
        // a defocus-asymmetric correlation produces -- while the long edges do
        // not. Chaining multiplies the bias 39 times; the global solve sees the
        // long edges disagree and splits the difference.
        let geom = plane_geom();
        let n = 40;
        let truth = planted_track(n, 0.045, Cx::new(0.0, 0.0));
        let bias = 1.0 - 3e-4;
        let mut edges = Vec::new();
        for i in 0..n - 1 {
            let rel = Similarity::relative(truth[i], truth[i + 1]).expect("relative");
            edges.push(edge(
                i,
                i + 1,
                Similarity {
                    a: rel.a.scale(bias),
                    b: rel.b,
                },
            ));
        }
        let mut long_edges = Vec::new();
        for i in (0..n - 13).step_by(3) {
            let rel = Similarity::relative(truth[i], truth[i + 13]).expect("relative");
            long_edges.push(edge(i, i + 13, rel));
        }
        let all: Vec<AlignEdge> = edges.iter().chain(long_edges.iter()).copied().collect();

        let (chain, hops) = solve_hops(&edges, n, 1);
        assert_eq!(hops[n - 1], n - 1, "the chain really is a chain");
        let chain_err = (0..n)
            .map(|k| chain[k].expect("placed").corner_err(truth[k], geom))
            .fold(0.0f64, f64::max);

        let g = solve_global(&all, n, &GlobalOptions::new(geom)).expect("solve");
        let global_err = (0..n)
            .map(|k| g[k].expect("placed").corner_err(truth[k], geom))
            .fold(0.0f64, f64::max);

        assert!(
            chain_err > 5.0,
            "the bias must actually compound or this proves nothing: {chain_err:.3} px"
        );
        assert!(
            global_err < chain_err / 3.0,
            "global {global_err:.3} px vs chain {chain_err:.3} px"
        );
    }

    #[test]
    fn the_parametric_solve_recovers_a_smooth_track_and_its_centre() {
        let geom = plane_geom();
        let n = 60;
        let centre = Cx::new(425.0, -449.0);
        let truth = planted_track(n, 0.05, centre);
        let mut edges = Vec::new();
        for span in [1usize, 7, 19] {
            for i in 0..n - span {
                let rel = Similarity::relative(truth[i], truth[i + span]).expect("relative");
                edges.push(edge(i, i + span, rel));
            }
        }
        let mut opts = PolyOptions::new(geom);
        opts.degree = 3;
        opts.translation = TranslationModel::FixedCentre;
        let sol = solve_poly(&edges, n, &opts).expect("solve");
        let c = sol.centre.expect("fixed centre requested");
        assert!(
            (c - centre).abs() < 1.0,
            "recovered centre {c:?} against planted {centre:?}"
        );
        let worst = (0..n)
            .map(|k| {
                sol.transforms[k]
                    .expect("placed")
                    .corner_err(truth[k], geom)
            })
            .fold(0.0f64, f64::max);
        assert!(worst < 0.05, "worst parametric placement {worst:.5} px");
    }

    #[test]
    fn cycle_consistency_is_zero_on_a_self_consistent_edge_set() {
        // The floor the measurements themselves impose. A perfectly consistent
        // set must read zero, or the metric is measuring the metric.
        let geom = plane_geom();
        let n = 12;
        let truth = planted_track(n, 0.03, Cx::new(10.0, -20.0));
        let mut edges = Vec::new();
        for i in 0..n {
            for j in i + 1..n {
                edges.push(edge(
                    i,
                    j,
                    Similarity::relative(truth[i], truth[j]).expect("relative"),
                ));
            }
        }
        let triples = cycle_consistency(&edges, geom, 0);
        assert!(triples.len() > 100, "not enough triples: {}", triples.len());
        let worst = triples.iter().map(|t| t.err).fold(0.0f64, f64::max);
        assert!(worst < 1e-9, "self-consistent set read {worst:e} px");
    }

    #[test]
    fn total_drift_measures_the_whole_bracket_not_one_pair() {
        let geom = plane_geom();
        let truth = planted_track(30, 0.04, Cx::ZERO);
        let placement: Placement = truth.iter().copied().map(Some).collect();
        let d = total_drift(&placement, geom);
        let last = truth[29].corner_err(Similarity::IDENTITY, geom);
        assert!((d - last).abs() < 1e-9);
        assert!(d > 8.0, "the plant should drift visibly: {d} px");
    }

    // ---- weighting -----------------------------------------------------

    #[test]
    fn inverse_variance_falls_back_rather_than_dividing_by_zero() {
        let e = AlignEdge {
            i: 0,
            j: 1,
            t: Similarity::IDENTITY,
            rms: 0.0,
            used: 0,
            lever: 0.0,
        };
        let rho = corner_radius(plane_geom());
        let (sa, sb) = Weighting::InverseVariance.sigmas(&e, rho);
        assert!(sa.is_finite() && sa > 0.0);
        assert!(sb.is_finite() && sb > 0.0);
        let (ua, ub) = Weighting::Unit.sigmas(&e, rho);
        assert_eq!((ua, ub), (1.0, 1.0));
    }

    // ---- resampling ----------------------------------------------------

    #[test]
    fn catmull_rom_reproduces_the_samples_at_integer_positions() {
        let data = texture(64, 64, 7);
        let p = PlaneRef::new(&data, 64, 64).expect("view");
        for (x, y) in [(10usize, 12usize), (33, 41), (60, 5)] {
            let s = sample_catmull_rom(p, x as f64, y as f64);
            assert!(
                (s - p.at(x, y)).abs() < 1e-3,
                "interpolator is not interpolating at ({x},{y}): {s} vs {}",
                p.at(x, y)
            );
        }
    }

    #[test]
    fn bilinear_costs_more_high_frequency_than_catmull_rom() {
        // A round trip that must be the identity: shift by +0.5 px and back.
        // Whatever is lost is the interpolator's own lowpass. This is the
        // miniature of the measurement the report has to make on real frames.
        let (w, h) = (128usize, 128usize);
        let data = texture(w, h, 4242);
        let p = PlaneRef::new(&data, w, h).expect("view");

        let hf = |v: &[f32]| -> f64 {
            let mut s = 0f64;
            for y in 4..h - 4 {
                for x in 4..w - 4 {
                    let lap = 4.0 * v[y * w + x] as f64
                        - v[y * w + x - 1] as f64
                        - v[y * w + x + 1] as f64
                        - v[(y - 1) * w + x] as f64
                        - v[(y + 1) * w + x] as f64;
                    s += lap * lap;
                }
            }
            s
        };

        let round = |r: Resampler| -> Vec<f32> {
            let mut a = vec![0f32; w * h];
            for y in 0..h {
                for x in 0..w {
                    a[y * w + x] = r.sample(p, x as f64 + 0.5, y as f64 + 0.5);
                }
            }
            let ap = PlaneRef::new(&a, w, h).expect("view");
            let mut b = vec![0f32; w * h];
            for y in 0..h {
                for x in 0..w {
                    b[y * w + x] = r.sample(ap, x as f64 - 0.5, y as f64 - 0.5);
                }
            }
            b
        };

        let base = hf(&data);
        let bl = hf(&round(Resampler::Bilinear)) / base;
        let cr = hf(&round(Resampler::CatmullRom)) / base;
        assert!(
            bl < 0.95,
            "the control is uninteresting if bilinear loses nothing: retained {bl:.4}"
        );
        assert!(
            cr > bl,
            "Catmull-Rom must retain more high frequency than bilinear: {cr:.4} vs {bl:.4}"
        );
    }

    #[test]
    fn a_gather_under_the_identity_is_the_identity() {
        let geom = PlaneGeometry {
            width: 64,
            height: 48,
        };
        let data = texture(64, 48, 11);
        let p = PlaneRef::new(&data, 64, 48).expect("view");
        let mut out = vec![0f32; geom.pixels()];
        gather_into(
            p,
            Similarity::IDENTITY,
            geom,
            Resampler::CatmullRom,
            &mut out,
        );
        // The interior must be bit-for-bit untouched: Catmull-Rom at integer
        // positions is the identity kernel, so any drift here is a coordinate
        // bug, not an interpolation cost.
        let mut worst = 0.0f32;
        for y in 2..46 {
            for x in 2..62 {
                let d = (data[y * 64 + x] - out[y * 64 + x]).abs();
                worst = worst.max(d);
            }
        }
        assert!(
            worst < 1e-3,
            "identity gather moved interior samples by {worst}"
        );

        // The border is a different claim and is stated separately: the plain
        // sampler clamps its support into the plane, so the outer two rings are
        // NOT the identity. This is the artefact `sample_checked` exists to
        // stop, and the test asserts the artefact is real rather than assuming
        // the clamp is harmless.
        let mut border = 0.0f32;
        for x in 0..64 {
            border = border.max((data[x] - out[x]).abs());
        }
        assert!(
            border > 1.0,
            "if the clamped border were harmless there would be no reason for \
             sample_checked; measured {border}"
        );
        assert!(
            Resampler::CatmullRom.sample_checked(p, 0.0, 0.0).is_none(),
            "the checked sampler must refuse a position whose support leaves the plane"
        );
        assert!(
            Resampler::CatmullRom.sample_checked(p, 2.0, 2.0).is_some(),
            "the checked sampler must accept a position fully inside the plane"
        );
    }

    // ---- numerics ------------------------------------------------------

    #[test]
    fn the_least_squares_core_refuses_an_underdetermined_system() {
        // The whole reason for a Cholesky rather than a minimum-norm solve.
        let mut sys = LeastSquares::new(3);
        sys.push(vec![(0, Cx::ONE)], Cx::real(2.0));
        sys.push(vec![(1, Cx::ONE)], Cx::real(3.0));
        assert!(
            sys.solve().is_none(),
            "column 2 is unconstrained; a solver that answers anyway is lying"
        );
    }

    #[test]
    fn the_least_squares_core_matches_a_known_solution() {
        let mut sys = LeastSquares::new(2);
        // x0 + x1 = 3, x0 - x1 = 1, and a redundant consistent row.
        sys.push(vec![(0, Cx::ONE), (1, Cx::ONE)], Cx::real(3.0));
        sys.push(vec![(0, Cx::ONE), (1, -Cx::ONE)], Cx::real(1.0));
        sys.push(vec![(0, Cx::real(2.0))], Cx::real(4.0));
        let x = sys.solve().expect("full rank");
        assert!((x[0] - Cx::real(2.0)).abs() < 1e-12, "{:?}", x[0]);
        assert!((x[1] - Cx::real(1.0)).abs() < 1e-12, "{:?}", x[1]);
    }

    #[test]
    fn downsample_averages_rather_than_subsamples() {
        let data: Vec<f32> = (0..16 * 16).map(|k| (k % 16) as f32).collect();
        let p = PlaneRef::new(&data, 16, 16).expect("view");
        let d = downsample(p, 4).expect("downsample");
        assert_eq!((d.width, d.height), (4, 4));
        // Column 0 of the coarse plane averages source columns 0..3.
        assert!((d.data[0] - 1.5).abs() < 1e-6, "{}", d.data[0]);
        assert!((d.data[3] - 13.5).abs() < 1e-6, "{}", d.data[3]);
    }

    #[test]
    fn a_plane_view_refuses_a_mismatched_buffer() {
        let data = vec![0f32; 10];
        assert!(PlaneRef::new(&data, 3, 3).is_none());
        assert!(PlaneRef::new(&data, 5, 2).is_some());
        assert!(PlaneRef::new(&data, 0, 0).is_none());
    }
}
