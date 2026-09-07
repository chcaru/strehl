//! M90 round 2 — measuring `rho_warp`, the inter-frame correlation of the fixed
//! pattern after warping.
//!
//! Round 1 left `rho_warp` unmeasured and recorded it as a **30.8x lever** on
//! predicted sigma at `n_eff` = 44 (fact 1194). This binary measures it.
//!
//! # What is actually measured
//!
//! PRNU is a fixed multiplicative pattern: photosite `u` responds `1 + p_u`.
//! The merge **gathers** rather than materialising warped frames, so at output
//! pixel `x` frame `k` contributes a resampled pattern error
//!
//! ```text
//! e_k(x) = sum_j w_j(t_k(x)) * p_{u_j(t_k(x))}
//! ```
//!
//! Two quantities fall out and **both are needed**; quoting either alone lets a
//! reader compute the noise floor wrong.
//!
//! - `W = Var(e_k)/kappa^2`, the *within-frame* attenuation. Every kernel wider
//!   than nearest is a lowpass, and PRNU is nearly white, so a resample
//!   attenuates the pattern inside a single frame. `W = 1` for `Nearest`.
//! - `rho = Cov(e_k,e_l)/sqrt(Var e_k Var e_l)`, the *between-frame*
//!   correlation. This is `rho_warp`.
//!
//! The merged PRNU variance over `n` frames is `F = W * [1/n + (n-1)/n * rho]`,
//! in units of the single-frame unresampled pattern variance. **`F` is the
//! primary measurand**, not `rho`: `F` is what `predicted_sigma` gets wrong, and
//! it is measurable without committing to the `W`/`rho` split. `n_prnu = 1/F` is
//! the effective number of independent PRNU samples the merge achieves —
//! `n_prnu = 1` is round 1's pessimistic bound, `n_prnu = n` is full averaging.
//!
//! # Two problems, and why neither costs anything
//!
//! **Temporal noise.** A pattern map estimated from real flats is `p + noise`,
//! and correlating a map with itself would score the noise as pattern. Solved by
//! estimating the pattern **twice from disjoint, interleaved flat halves** and
//! only ever correlating an `A` against a `B`. The temporal term then vanishes
//! in expectation from numerator *and* denominator, so the instrument needs no
//! estimate of the noise level and no floor subtraction.
//!
//! **The `n^2` sum.** `F` needs `sum_{k,l} Cov(e_k,e_l)` over all `n^2` pairs.
//! But that is exactly `Cov(sum_k e_k, sum_l e_l)`, so accumulating the two
//! merged maps gives `F` in **O(n)**. This is not an approximation of the merge;
//! it is the merge, run on the pattern instead of on the scene.
//!
//! # Provenance of the warps
//!
//! Real and measured, from M86's committed edge tables, solved with `align.rs`'s
//! own solvers. `align.rs` is read-only to this milestone: it is called, never
//! edited.
//!
//! ```text
//! cargo run --release --example m90-rho -- prnu   --flats <DIR> [--hp 30]
//! cargo run --release --example m90-rho -- rho    --edges <CSV> [--hp 30]
//! cargo run --release --example m90-rho -- control
//! ```

use std::path::{Path, PathBuf};

use anyhow::{Context, Result, bail};
use strehl_core::align::{
    AlignEdge, GlobalOptions, PlaneRef, PolyOptions, Resampler, Similarity, SimilarityParams,
    TranslationModel, Weighting, solve_global, solve_poly,
};
use strehl_core::clip::CONTAINER_MAX_DN;
use strehl_core::plane::{PlaneGeometry, QuadSource, green_luma_with_clip};

/// Default high-pass radius, in plane px. Round 1 used 30 on the photosite
/// grid; the registered bandwidth diagnostic repeats the measurement at 8.
const HP_RADIUS: usize = 30;

/// Only flats in this luma band contribute to a pattern estimate. Below it the
/// temporal noise dominates the pattern; above it the sensor is near enough to
/// saturation that the response is no longer linear.
const FLAT_MIN_DN: f64 = 3000.0;
const FLAT_MAX_DN: f64 = 14000.0;

/// Sub-sampling stride for the correlation statistics. 3516x2344 at stride 4 is
/// ~515k points, which puts the sampling error on a correlation near 0.14% —
/// far below every effect this milestone reports.
const STRIDE: usize = 4;

/// Multiple of the high-pass radius excluded from every plane edge.
///
/// `box_mean` is edge-clamped, so within one radius of a border it is not the
/// local mean of a full window and `I / box(I) - 1` retains illumination
/// curvature that no amount of frame averaging removes. That residual is a
/// fixed, smooth field: it does not decorrelate under a warp, so it biases `F`
/// upward, and the bias grows with the radius. Excluding two radii makes every
/// surviving point's window fully interior.
const MARGIN_RADII: usize = 2;

/// Radial bins, as a fraction of the corner radius.
const RADIAL_BINS: usize = 8;

/// A radial bin is admitted only if `Nearest` reproduces its own exact
/// identity, `W = 1`, to this tolerance. See the validity mask in `cmd_rho`.
const W_NEAREST_TOL: f64 = 0.05;

/// The plant for the N3 decorrelation bound, in plane px. Far beyond every
/// kernel's support.
const BIG_SHIFT_PX: f64 = 50.0;

// ---------------------------------------------------------------------------
// small numerics
// ---------------------------------------------------------------------------

/// Separable sliding-window box mean, radius `r`, edge-clamped.
fn box_mean(src: &[f32], w: usize, h: usize, r: usize, dst: &mut [f32]) {
    assert_eq!(src.len(), w * h);
    assert_eq!(dst.len(), w * h);
    let mut tmp = vec![0f32; w * h];
    for y in 0..h {
        let row = &src[y * w..(y + 1) * w];
        let out = &mut tmp[y * w..(y + 1) * w];
        let mut acc = 0f64;
        for x in 0..=r.min(w - 1) {
            acc += f64::from(row[x]);
        }
        let mut lo = 0usize;
        let mut hi = r.min(w - 1);
        for (x, o) in out.iter_mut().enumerate() {
            let want_lo = x.saturating_sub(r);
            let want_hi = (x + r).min(w - 1);
            while hi < want_hi {
                hi += 1;
                acc += f64::from(row[hi]);
            }
            while lo < want_lo {
                acc -= f64::from(row[lo]);
                lo += 1;
            }
            *o = (acc / (hi - lo + 1) as f64) as f32;
        }
    }
    for x in 0..w {
        let mut acc = 0f64;
        for y in 0..=r.min(h - 1) {
            acc += f64::from(tmp[y * w + x]);
        }
        let mut lo = 0usize;
        let mut hi = r.min(h - 1);
        for y in 0..h {
            let want_lo = y.saturating_sub(r);
            let want_hi = (y + r).min(h - 1);
            while hi < want_hi {
                hi += 1;
                acc += f64::from(tmp[hi * w + x]);
            }
            while lo < want_lo {
                acc -= f64::from(tmp[lo * w + x]);
                lo += 1;
            }
            dst[y * w + x] = (acc / (hi - lo + 1) as f64) as f32;
        }
    }
}

/// Streaming covariance of two equal-length sample sets.
#[derive(Clone, Copy, Default)]
struct Cov {
    n: u64,
    sx: f64,
    sy: f64,
    sxy: f64,
    sxx: f64,
    syy: f64,
}

impl Cov {
    #[inline]
    fn push(&mut self, x: f64, y: f64) {
        self.n += 1;
        self.sx += x;
        self.sy += y;
        self.sxy += x * y;
        self.sxx += x * x;
        self.syy += y * y;
    }

    fn cov(&self) -> f64 {
        if self.n < 2 {
            return f64::NAN;
        }
        let n = self.n as f64;
        (self.sxy - self.sx * self.sy / n) / (n - 1.0)
    }

    /// Ordinary Pearson `r`. Used only by the placebo, where the cross-estimate
    /// normalisation is 0/0 by construction.
    fn pearson(&self) -> f64 {
        if self.n < 2 {
            return f64::NAN;
        }
        let n = self.n as f64;
        let vx = (self.sxx - self.sx * self.sx / n) / (n - 1.0);
        let vy = (self.syy - self.sy * self.sy / n) / (n - 1.0);
        if vx <= 0.0 || vy <= 0.0 {
            return f64::NAN;
        }
        self.cov() / (vx * vy).sqrt()
    }
}

// ---------------------------------------------------------------------------
// the pattern maps
// ---------------------------------------------------------------------------

/// Two independent estimates of the same fixed pattern, on the green-luma
/// plane, expressed as relative deviation from the local mean.
struct Pattern {
    geom: PlaneGeometry,
    a: Vec<f32>,
    b: Vec<f32>,
    n_a: usize,
    n_b: usize,
    hp: usize,
}

impl Pattern {
    fn cache_path(hp: usize) -> PathBuf {
        PathBuf::from(format!("experiments/M90-prnu/out/cache/pattern-hp{hp}.bin"))
    }

    fn save(&self) -> Result<()> {
        let p = Self::cache_path(self.hp);
        if let Some(d) = p.parent() {
            std::fs::create_dir_all(d)?;
        }
        let mut v: Vec<u8> = Vec::with_capacity(16 + self.a.len() * 8);
        v.extend_from_slice(&(self.geom.width as u32).to_le_bytes());
        v.extend_from_slice(&(self.geom.height as u32).to_le_bytes());
        v.extend_from_slice(&(self.n_a as u32).to_le_bytes());
        v.extend_from_slice(&(self.n_b as u32).to_le_bytes());
        for x in &self.a {
            v.extend_from_slice(&x.to_le_bytes());
        }
        for x in &self.b {
            v.extend_from_slice(&x.to_le_bytes());
        }
        std::fs::write(&p, &v)?;
        println!("  cached pattern -> {} ({} bytes)", p.display(), v.len());
        Ok(())
    }

    fn load(hp: usize) -> Result<Self> {
        let p = Self::cache_path(hp);
        let v = std::fs::read(&p)
            .with_context(|| format!("no cached pattern at {} — run `prnu` first", p.display()))?;
        let rd_u32 = |o: usize| u32::from_le_bytes([v[o], v[o + 1], v[o + 2], v[o + 3]]) as usize;
        let (w, h, n_a, n_b) = (rd_u32(0), rd_u32(4), rd_u32(8), rd_u32(12));
        let px = w * h;
        if v.len() != 16 + px * 8 {
            bail!("cached pattern {} is truncated", p.display());
        }
        let mut a = Vec::with_capacity(px);
        let mut b = Vec::with_capacity(px);
        for i in 0..px {
            let o = 16 + i * 4;
            a.push(f32::from_le_bytes([v[o], v[o + 1], v[o + 2], v[o + 3]]));
        }
        for i in 0..px {
            let o = 16 + px * 4 + i * 4;
            b.push(f32::from_le_bytes([v[o], v[o + 1], v[o + 2], v[o + 3]]));
        }
        Ok(Pattern {
            geom: PlaneGeometry {
                width: w,
                height: h,
            },
            a,
            b,
            n_a,
            n_b,
            hp,
        })
    }
}

fn list_arw(dir: &Path) -> Result<Vec<PathBuf>> {
    let mut v: Vec<PathBuf> = std::fs::read_dir(dir)
        .with_context(|| format!("listing {}", dir.display()))?
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| {
            p.extension()
                .and_then(|e| e.to_str())
                .is_some_and(|e| e.eq_ignore_ascii_case("arw"))
        })
        .collect();
    v.sort();
    Ok(v)
}

/// Build the two interleaved pattern estimates from a directory of flats.
///
/// Interleaved rather than split-in-half on purpose: the flats were shot as an
/// exposure sweep, so a contiguous split would give the two halves different
/// signal distributions and the cross-estimate normalisation would compare two
/// different things.
fn cmd_prnu(flats: &Path, hp: usize) -> Result<()> {
    let paths = list_arw(flats)?;
    if paths.is_empty() {
        bail!("no ARW under {}", flats.display());
    }
    println!("prnu: {} ARW under {}", paths.len(), flats.display());

    let first = strehl_raw::decode(&paths[0]).context("decoding the first flat")?;
    let geom = first.geometry();
    let black = first.levels.black;
    drop(first);
    let px = geom.pixels();
    println!("  plane {}x{} ({} px)", geom.width, geom.height, px);

    let mut acc_a = vec![0f64; px];
    let mut acc_b = vec![0f64; px];
    let (mut n_a, mut n_b) = (0usize, 0usize);
    let mut luma = vec![0f32; px];
    let mut clipped = vec![false; px];
    let mut lp = vec![0f32; px];
    let mut used = 0usize;

    for p in &paths {
        let frame = strehl_raw::decode(p).with_context(|| format!("decoding {}", p.display()))?;
        green_luma_with_clip(&frame, black, CONTAINER_MAX_DN, &mut luma, &mut clipped);
        let mean = luma.iter().map(|v| f64::from(*v)).sum::<f64>() / px as f64;
        if !(FLAT_MIN_DN..=FLAT_MAX_DN).contains(&mean) {
            continue;
        }
        box_mean(&luma, geom.width, geom.height, hp, &mut lp);
        // Interleave by *accepted* index so both halves see the same exposures.
        let to_a = used % 2 == 0;
        used += 1;
        let acc = if to_a { &mut acc_a } else { &mut acc_b };
        for i in 0..px {
            let l = f64::from(lp[i]);
            if l > 0.0 {
                acc[i] += f64::from(luma[i]) / l - 1.0;
            }
        }
        if to_a {
            n_a += 1;
        } else {
            n_b += 1;
        }
        if used % 25 == 0 {
            println!("  {used} flats folded (mean {mean:.0} DN)");
        }
    }
    if n_a == 0 || n_b == 0 {
        bail!("no flats in the {FLAT_MIN_DN}..{FLAT_MAX_DN} DN band");
    }
    println!("  accepted {used} flats: A={n_a}, B={n_b}, high-pass radius {hp} px");

    let a: Vec<f32> = acc_a.iter().map(|v| (v / n_a as f64) as f32).collect();
    let b: Vec<f32> = acc_b.iter().map(|v| (v / n_b as f64) as f32).collect();
    let pat = Pattern {
        geom,
        a,
        b,
        n_a,
        n_b,
        hp,
    };

    // The cross-estimate covariance of the two halves IS kappa^2 on the luma
    // plane, with the temporal term already cancelled. Report it: it is a free
    // replication and it prices the G1/G2 question.
    let mut c = Cov::default();
    for i in (0..px).step_by(7) {
        c.push(f64::from(pat.a[i]), f64::from(pat.b[i]));
    }
    let k = c.cov().max(0.0).sqrt();
    println!("  kappa(green luma) = {:.6}% (cross-estimate)", k * 100.0);
    pat.save()
}

// ---------------------------------------------------------------------------
// warps
// ---------------------------------------------------------------------------

struct EdgeTable {
    edges: Vec<AlignEdge>,
    n: usize,
    geom: PlaneGeometry,
    case: String,
}

/// Minimal reader for M86's committed edge schema. Deliberately independent of
/// M86's own reader: this milestone must not be able to break by editing M86's
/// example, and a second reader is a cheap cross-check on the schema.
fn read_edges(path: &Path) -> Result<EdgeTable> {
    let text =
        std::fs::read_to_string(path).with_context(|| format!("reading {}", path.display()))?;
    let mut lines = text.lines();
    let header = lines.next().context("empty edge table")?;
    let cols: Vec<&str> = header.split(',').map(|s| s.trim()).collect();
    let idx = |name: &str| -> Result<usize> {
        cols.iter()
            .position(|c| *c == name)
            .with_context(|| format!("edge table has no `{name}` column"))
    };
    let (ci, cj) = (idx("ref")?, idx("mov")?);
    let (cg, crot) = (idx("g")?, idx("rot")?);
    let (cax, cay) = (idx("ax")?, idx("ay")?);
    let (cst, cused) = (idx("status")?, idx("used")?);
    let (crms, clev) = (idx("rms")?, idx("lever_rms")?);
    let (cpw, cph) = (idx("plane_w")?, idx("plane_h")?);
    let ccase = idx("case")?;

    let mut edges = Vec::new();
    let mut n = 0usize;
    let (mut pw, mut ph) = (0usize, 0usize);
    let mut case = String::new();
    for line in lines {
        if line.trim().is_empty() {
            continue;
        }
        let f: Vec<&str> = line.split(',').map(|s| s.trim()).collect();
        if f.len() < cols.len() {
            continue;
        }
        if f[cst] != "ok" {
            continue;
        }
        let i: usize = f[ci].parse()?;
        let j: usize = f[cj].parse()?;
        n = n.max(i + 1).max(j + 1);
        pw = f[cpw].parse().unwrap_or(pw);
        ph = f[cph].parse().unwrap_or(ph);
        if case.is_empty() {
            case = f[ccase].to_string();
        }
        edges.push(AlignEdge {
            i,
            j,
            t: Similarity::from_params(SimilarityParams {
                ax: f[cax].parse().unwrap_or(0.0),
                ay: f[cay].parse().unwrap_or(0.0),
                g: f[cg].parse().unwrap_or(0.0),
                rot: f[crot].parse().unwrap_or(0.0),
            }),
            used: f[cused].parse().unwrap_or(0),
            rms: f[crms].parse().unwrap_or(0.0),
            lever: f[clev].parse().unwrap_or(1.0),
        });
    }
    if edges.is_empty() {
        bail!("no `ok` edges in {}", path.display());
    }
    Ok(EdgeTable {
        edges,
        n,
        geom: PlaneGeometry {
            width: pw,
            height: ph,
        },
        case,
    })
}

/// Solve a placement two independent ways, so a result that depends on the
/// solver is visible as a result that depends on the solver.
fn placements(t: &EdgeTable) -> Vec<(String, Vec<Option<Similarity>>)> {
    let mut out = Vec::new();
    let mut g = GlobalOptions::new(t.geom);
    g.weighting = Weighting::Unit;
    if let Some(p) = solve_global(&t.edges, t.n, &g) {
        out.push(("S3-ba-unit".to_string(), p));
    }
    let mut q = PolyOptions::new(t.geom);
    q.degree = 4;
    q.translation = TranslationModel::Poly(4);
    if let Some(s) = solve_poly(&t.edges, t.n, &q) {
        out.push(("S4-poly4".to_string(), s.transforms));
    }
    out
}

// ---------------------------------------------------------------------------
// the measurement core
// ---------------------------------------------------------------------------

/// One evaluation of `F` for a given pattern pair, transform list and resampler.
struct Merged {
    /// `F` overall and per radial bin, plus the point census per bin.
    f_all: f64,
    f_bin: Vec<f64>,
    n_bin: Vec<u64>,
    /// Raw numerator and denominator per bin, so bins can be re-pooled exactly
    /// after the validity mask is applied.
    num_bin: Vec<f64>,
    den_bin: Vec<f64>,
    /// Mean within-frame attenuation `W`, and the raw normaliser.
    w_mean: f64,
    w_bin: Vec<f64>,
    w_num_bin: Vec<f64>,
    /// Share of the total unwarped pattern variance held by each radial bin,
    /// times the number of bins — 1.0 everywhere would mean a stationary field.
    var_share: Vec<f64>,
    c00: f64,
    /// Placebo diagnostic: the raw Pearson `r` of the two merged maps.
    r_merged: f64,
    points: u64,
}

impl Merged {
    /// Pool the listed bins exactly, by summing numerators and denominators
    /// rather than averaging ratios.
    fn pooled(&self, keep: &[bool]) -> (f64, f64, u64) {
        let (mut num, mut den, mut wn, mut n) = (0.0, 0.0, 0.0, 0u64);
        for b in 0..RADIAL_BINS {
            if keep[b] {
                num += self.num_bin[b];
                den += self.den_bin[b];
                wn += self.w_num_bin[b];
                n += self.n_bin[b];
            }
        }
        (num / den, wn / den, n)
    }
}

/// The sample lattice, with each point's radial bin, pre-filtered so that every
/// listed transform stays inside the plane for every point.
struct Lattice {
    xs: Vec<f32>,
    ys: Vec<f32>,
    bin: Vec<u8>,
}

fn lattice(geom: PlaneGeometry, ts: &[Similarity], resampler: Resampler, margin: usize) -> Lattice {
    let (cx, cy) = (geom.width as f64 * 0.5, geom.height as f64 * 0.5);
    let rmax = (cx * cx + cy * cy).sqrt();
    let s = resampler.support();
    let m = margin as f64;
    let (mut xs, mut ys, mut bin) = (Vec::new(), Vec::new(), Vec::new());
    let mut y = 0usize;
    while y < geom.height {
        let mut x = 0usize;
        while x < geom.width {
            let (fx, fy) = (x as f64, y as f64);
            // The point itself must be interior, and so must every frame's
            // source position: a warped sample that lands in the contaminated
            // border carries that border's residual into the interior.
            let ok = fx >= m
                && fy >= m
                && fx <= geom.width as f64 - 1.0 - m
                && fy <= geom.height as f64 - 1.0 - m
                && ts.iter().all(|t| {
                    let (sx, sy) = t.apply_at(fx, fy, cx, cy);
                    sx >= (s - 0.5).max(m)
                        && sy >= (s - 0.5).max(m)
                        && sx <= geom.width as f64 - 0.5 - s.max(m + 0.5)
                        && sy <= geom.height as f64 - 0.5 - s.max(m + 0.5)
                });
            if ok {
                let r = ((fx - cx).powi(2) + (fy - cy).powi(2)).sqrt() / rmax;
                let b = ((r * RADIAL_BINS as f64) as usize).min(RADIAL_BINS - 1);
                xs.push(fx as f32);
                ys.push(fy as f32);
                bin.push(b as u8);
            }
            x += STRIDE;
        }
        y += STRIDE;
    }
    Lattice { xs, ys, bin }
}

/// Run the merge on the pattern. `O(n)` in frames — see the module header.
fn merge_pattern(
    pa: &[f32],
    pb: &[f32],
    geom: PlaneGeometry,
    ts: &[Similarity],
    resampler: Resampler,
    lat: &Lattice,
) -> Merged {
    let a = PlaneRef::from_geometry(pa, geom).expect("pattern A plane");
    let b = PlaneRef::from_geometry(pb, geom).expect("pattern B plane");
    let (cx, cy) = (geom.width as f64 * 0.5, geom.height as f64 * 0.5);
    let np = lat.xs.len();
    let mut ma = vec![0f64; np];
    let mut mb = vec![0f64; np];
    // Within-frame attenuation, accumulated per frame then averaged.
    let mut w_acc = 0f64;
    let mut w_acc_bin = vec![0f64; RADIAL_BINS];

    for t in ts {
        let mut cw = Cov::default();
        let mut cwb = vec![Cov::default(); RADIAL_BINS];
        for i in 0..np {
            let (sx, sy) = t.apply_at(f64::from(lat.xs[i]), f64::from(lat.ys[i]), cx, cy);
            let va = f64::from(resampler.sample(a, sx, sy));
            let vb = f64::from(resampler.sample(b, sx, sy));
            ma[i] += va;
            mb[i] += vb;
            cw.push(va, vb);
            cwb[lat.bin[i] as usize].push(va, vb);
        }
        w_acc += cw.cov();
        for b in 0..RADIAL_BINS {
            w_acc_bin[b] += cwb[b].cov();
        }
    }
    let n = ts.len() as f64;
    for i in 0..np {
        ma[i] /= n;
        mb[i] /= n;
    }

    // The normaliser: the un-warped cross-estimate variance of the pattern, on
    // exactly the same points, so geometry cannot leak into the ratio.
    let mut c0 = Cov::default();
    let mut c0b = vec![Cov::default(); RADIAL_BINS];
    for i in 0..np {
        let (x, y) = (lat.xs[i] as usize, lat.ys[i] as usize);
        let o = y * geom.width + x;
        c0.push(f64::from(pa[o]), f64::from(pb[o]));
        c0b[lat.bin[i] as usize].push(f64::from(pa[o]), f64::from(pb[o]));
    }
    let c00 = c0.cov();

    let mut all = Cov::default();
    let mut bins = vec![Cov::default(); RADIAL_BINS];
    for i in 0..np {
        all.push(ma[i], mb[i]);
        bins[lat.bin[i] as usize].push(ma[i], mb[i]);
    }
    Merged {
        // Per bin, both numerator and denominator are that bin's own, so a
        // non-stationary field cannot leak between bins.
        f_bin: (0..RADIAL_BINS)
            .map(|b| bins[b].cov() / c0b[b].cov())
            .collect(),
        w_bin: (0..RADIAL_BINS)
            .map(|b| w_acc_bin[b] / n / c0b[b].cov())
            .collect(),
        num_bin: (0..RADIAL_BINS).map(|b| bins[b].cov()).collect(),
        den_bin: (0..RADIAL_BINS).map(|b| c0b[b].cov()).collect(),
        w_num_bin: (0..RADIAL_BINS).map(|b| w_acc_bin[b] / n).collect(),
        var_share: (0..RADIAL_BINS).map(|b| c0b[b].cov() / c00).collect(),
        f_all: all.cov() / c00,
        n_bin: bins.iter().map(|c| c.n).collect(),
        w_mean: w_acc / n / c00,
        c00,
        r_merged: all.pearson(),
        points: all.n,
    }
}

/// Invert `F = W * [1/n + (n-1)/n * rho]` for the implied scalar `rho`, for
/// continuity with fact 1194's parameterisation.
fn implied_rho(f: f64, w: f64, n: usize) -> f64 {
    if n < 2 || w <= 0.0 {
        return f64::NAN;
    }
    let n = n as f64;
    (f / w - 1.0 / n) * n / (n - 1.0)
}

// ---------------------------------------------------------------------------
// controls
// ---------------------------------------------------------------------------

/// Deterministic LCG. No RNG dependency exists in this workspace and a control
/// that depends on one is a control that changes when the dependency does.
struct Lcg(u64);

impl Lcg {
    fn next_unit(&mut self) -> f64 {
        self.0 = self
            .0
            .wrapping_mul(6364136223846793005)
            .wrapping_add(1442695040888963407);
        ((self.0 >> 11) as f64) / ((1u64 << 53) as f64)
    }
    /// Box-Muller, one of the pair.
    fn normal(&mut self) -> f64 {
        let u1 = self.next_unit().max(1e-12);
        let u2 = self.next_unit();
        (-2.0 * u1.ln()).sqrt() * (std::f64::consts::TAU * u2).cos()
    }
}

const CTRL_W: usize = 1024;
const CTRL_H: usize = 768;

/// A synthetic white pattern plus two independent noise realisations, so the
/// instrument's arithmetic can be checked against a value derived by hand.
fn synth_pattern(kappa: f64, noise: f64, seed: u64) -> (Vec<f32>, Vec<f32>) {
    let px = CTRL_W * CTRL_H;
    let mut rp = Lcg(seed);
    let mut ra = Lcg(seed ^ 0x5151_5151);
    let mut rb = Lcg(seed ^ 0xA2A2_A2A2);
    let mut a = Vec::with_capacity(px);
    let mut b = Vec::with_capacity(px);
    for _ in 0..px {
        let p = kappa * rp.normal();
        a.push((p + noise * ra.normal()) as f32);
        b.push((p + noise * rb.normal()) as f32);
    }
    (a, b)
}

fn shift(dx: f64, dy: f64) -> Similarity {
    Similarity::from_params(SimilarityParams {
        ax: dx,
        ay: dy,
        g: 0.0,
        rot: 0.0,
    })
}

const RESAMPLERS: [(&str, Resampler); 3] = [
    ("Nearest", Resampler::Nearest),
    ("Bilinear", Resampler::Bilinear),
    ("CatmullRom", Resampler::CatmullRom),
];

/// P1's predicted values, derived from separable kernel overlap at a (0.5, 0.5)
/// px shift **before** the control was run. See PREREGISTRATION-rho.md §4.
const P1_PREDICTED: [f64; 3] = [0.0000, 0.2500, 0.3164];
const P1_TOL: f64 = 0.02;

/// The within-frame attenuation `W` of a (0.5, 0.5) px resample, `sum(w^2)`
/// squared for the separable 2D kernel. Not a registered bar — derived after
/// the fact to diagnose the P1 scatter, and labelled as such in the report.
const W_PREDICTED: [f64; 3] = [1.0000, 0.2500, 0.4104];

/// Run the two-frame ladder at a given temporal-noise level and return
/// `(c01, W_frame1)` per resampler.
fn ladder_at(noise: f64, seed: u64) -> Vec<(f64, f64)> {
    let geom = PlaneGeometry {
        width: CTRL_W,
        height: CTRL_H,
    };
    let (pa, pb) = synth_pattern(0.0031, noise, seed);
    let ts2 = [Similarity::IDENTITY, shift(0.5, 0.5)];
    RESAMPLERS
        .iter()
        .map(|(_, r)| {
            let lat = lattice(geom, &ts2, *r, 0);
            let m = merge_pattern(&pa, &pb, geom, &ts2, *r, &lat);
            (2.0 * m.f_all - m.w_mean, 2.0 * m.w_mean - 1.0)
        })
        .collect()
}

fn cmd_control() -> Result<()> {
    let geom = PlaneGeometry {
        width: CTRL_W,
        height: CTRL_H,
    };
    println!("=== registered controls, {CTRL_W}x{CTRL_H} synthetic plane ===");
    println!("(bars are from experiments/M90-prnu/PREREGISTRATION-rho.md, committed at c2692ec)\n");
    let kappa = 0.0031;
    let noise = 0.0100;
    let (pa, pb) = synth_pattern(kappa, noise, 0x9051_2E17);
    let mut fails: Vec<String> = Vec::new();

    // -- P1: kernel ladder against hand-derived values --------------------
    println!("--- P1 kernel ladder: two frames, (0,0) and (+0.5,+0.5) px ---");
    println!(
        "{:>12} {:>9} {:>9} {:>11} {:>11} {:>8}",
        "resampler", "support", "W(frame1)", "measured", "predicted", "bar"
    );
    let ts2 = [Similarity::IDENTITY, shift(0.5, 0.5)];
    let mut ladder = Vec::new();
    for (k, (name, r)) in RESAMPLERS.iter().enumerate() {
        let lat = lattice(geom, &ts2, *r, 0);
        let m = merge_pattern(&pa, &pb, geom, &ts2, *r, &lat);
        // For two frames F = (C00 + 2*C01 + C11)/(4*C00) and w_mean is
        // (C00 + C11)/(2*C00), so the cross term is 2F - w_mean.
        let c01 = 2.0 * m.f_all - m.w_mean;
        ladder.push(c01);
        let ok = (c01 - P1_PREDICTED[k]).abs() <= P1_TOL;
        if !ok {
            fails.push(format!(
                "P1 {name}: {c01:.4} vs predicted {:.4}",
                P1_PREDICTED[k]
            ));
        }
        println!(
            "{:>12} {:>9.1} {:>9.4} {:>11.4} {:>11.4} {:>8}",
            name,
            r.support(),
            2.0 * m.w_mean - 1.0,
            c01,
            P1_PREDICTED[k],
            if ok { "PASS" } else { "FAIL" }
        );
    }
    let monotone = ladder[0] < ladder[1] && ladder[1] < ladder[2];
    println!(
        "  ordering Nearest < Bilinear < CatmullRom: {}",
        if monotone { "PASS" } else { "FAIL" }
    );
    if !monotone {
        fails.push("P1 ordering not strictly increasing".into());
    }

    // -- N2: identity null -------------------------------------------------
    println!("\n--- N2 identity null: F must be 1.000 (bar +/-0.01) ---");
    println!(
        "{:>12} {:>12} {:>12} {:>8}",
        "resampler", "F", "n_prnu", "bar"
    );
    let ts_id: Vec<Similarity> = vec![Similarity::IDENTITY; 8];
    for (name, r) in RESAMPLERS.iter() {
        let lat = lattice(geom, &ts_id, *r, 0);
        let m = merge_pattern(&pa, &pb, geom, &ts_id, *r, &lat);
        let ok = (m.f_all - 1.0).abs() <= 0.01;
        if !ok {
            fails.push(format!("N2 {name}: F = {:.4}", m.f_all));
        }
        println!(
            "{:>12} {:>12.4} {:>12.3} {:>8}",
            name,
            m.f_all,
            1.0 / m.f_all,
            if ok { "PASS" } else { "FAIL" }
        );
    }

    // -- N3: decorrelation bound -------------------------------------------
    let nfr = 8usize;
    println!(
        "\n--- N3 decorrelation bound: {BIG_SHIFT_PX} px per frame, F must be < 2/n = {:.4} ---",
        2.0 / nfr as f64
    );
    println!(
        "{:>12} {:>12} {:>12} {:>8}",
        "resampler", "F", "n_prnu", "bar"
    );
    let ts_big: Vec<Similarity> = (0..nfr)
        .map(|k| shift(BIG_SHIFT_PX * k as f64, BIG_SHIFT_PX * k as f64))
        .collect();
    for (name, r) in RESAMPLERS.iter() {
        let lat = lattice(geom, &ts_big, *r, 0);
        let m = merge_pattern(&pa, &pb, geom, &ts_big, *r, &lat);
        let ok = m.f_all < 2.0 / nfr as f64;
        if !ok {
            fails.push(format!("N3 {name}: F = {:.4}", m.f_all));
        }
        println!(
            "{:>12} {:>12.4} {:>12.3} {:>8}",
            name,
            m.f_all,
            1.0 / m.f_all,
            if ok { "PASS" } else { "FAIL" }
        );
    }

    // -- N1: placebo -------------------------------------------------------
    println!("\n--- N1 placebo: independent fields, NO shared pattern ---");
    println!("  bar: induced covariance under 5% of the real-pattern value\n");
    println!(
        "{:>12} {:>14} {:>14} {:>10} {:>8}",
        "resampler", "cov(pattern)", "cov(placebo)", "ratio", "bar"
    );
    let (za, zb) = {
        let px = CTRL_W * CTRL_H;
        let mut r1 = Lcg(0x1234_5678);
        let mut r2 = Lcg(0x8765_4321);
        let mut a = Vec::with_capacity(px);
        let mut b = Vec::with_capacity(px);
        for _ in 0..px {
            a.push((kappa * r1.normal()) as f32);
            b.push((kappa * r2.normal()) as f32);
        }
        (a, b)
    };
    let ts_real: Vec<Similarity> = (0..nfr)
        .map(|k| shift(0.37 * k as f64, -0.21 * k as f64))
        .collect();
    for (name, r) in RESAMPLERS.iter() {
        let lat = lattice(geom, &ts_real, *r, 0);
        let real = merge_pattern(&pa, &pb, geom, &ts_real, *r, &lat);
        let plac = merge_pattern(&za, &zb, geom, &ts_real, *r, &lat);
        let num_real = real.f_all * real.c00;
        let num_plac = plac.f_all.abs() * plac.c00.abs();
        let ratio = if num_real.abs() > 0.0 {
            (num_plac / num_real).abs()
        } else {
            f64::INFINITY
        };
        let ok = ratio < 0.05;
        if !ok {
            fails.push(format!("N1 {name}: placebo ratio {ratio:.4}"));
        }
        println!(
            "{:>12} {:>14.3e} {:>14.3e} {:>10.4} {:>8}",
            name,
            num_real,
            num_plac,
            ratio,
            if ok { "PASS" } else { "FAIL" }
        );
        println!(
            "             placebo merged Pearson r = {:+.5}",
            plac.r_merged
        );
    }

    println!("\n--- control verdict ---");
    if fails.is_empty() {
        println!("  all registered controls PASS");
    } else {
        for f in &fails {
            println!("  FAIL  {f}");
        }
    }

    // -- unregistered diagnostic: is the P1 scatter sampling noise? --------
    //
    // The registered control runs at noise/kappa = 3.2, which is one flat's
    // worth of temporal noise, far harsher than the ~180-flat averages the real
    // measurement uses. If the residuals are sampling error and not a bias in
    // the estimator, they must shrink toward the analytic values as the noise
    // falls. This arm is DIAGNOSTIC, added after seeing the P1 scatter, and
    // carries no pass/fail — it is reported as such.
    println!("\n--- diagnostic (unregistered, added after P1): noise sweep ---");
    println!("  analytic c01 = {P1_PREDICTED:?}, analytic W(frame1) = {W_PREDICTED:?}");
    println!(
        "{:>10} {:>8} {:>26} {:>26}",
        "noise", "n/kappa", "c01 err vs analytic", "W err vs analytic"
    );
    for (tag, noise) in [
        ("1 flat", 0.0100),
        ("16 flats", 0.0025),
        ("180 flats", 0.000745),
        ("none", 0.0),
    ] {
        let l = ladder_at(noise, 0x9051_2E17);
        let ce: Vec<String> = l
            .iter()
            .zip(P1_PREDICTED)
            .map(|((c, _), p)| format!("{:+.4}", c - p))
            .collect();
        let we: Vec<String> = l
            .iter()
            .zip(W_PREDICTED)
            .map(|((_, w), p)| format!("{:+.4}", w - p))
            .collect();
        println!(
            "{:>10} {:>8.2} {:>26} {:>26}",
            tag,
            noise / 0.0031,
            ce.join(" "),
            we.join(" ")
        );
    }

    // At zero noise the estimator is exact algebra, so any residual must be the
    // sampling error of a covariance over the lattice: SD = 1/sqrt(N). Eight
    // seeds separate "the instrument is biased" from "that was one draw".
    println!("\n--- diagnostic: zero-noise seed sweep, 8 seeds ---");
    let seeds: Vec<u64> = (0..8)
        .map(|k| 0x9051_2E17u64.wrapping_add(k * 0x9E37_79B9))
        .collect();
    let runs: Vec<Vec<(f64, f64)>> = seeds.iter().map(|s| ladder_at(0.0, *s)).collect();
    let npts = {
        let g = PlaneGeometry {
            width: CTRL_W,
            height: CTRL_H,
        };
        lattice(g, &[Similarity::IDENTITY], Resampler::CatmullRom, 0)
            .xs
            .len()
    };
    println!(
        "  theoretical sampling SD of a lattice covariance ratio = 1/sqrt({npts}) = {:.4}",
        1.0 / (npts as f64).sqrt()
    );
    println!(
        "{:>12} {:>12} {:>12} {:>12}",
        "resampler", "mean c01err", "sd c01err", "analytic"
    );
    for (k, (name, _)) in RESAMPLERS.iter().enumerate() {
        let e: Vec<f64> = runs.iter().map(|r| r[k].0 - P1_PREDICTED[k]).collect();
        let m = e.iter().sum::<f64>() / e.len() as f64;
        let sd = (e.iter().map(|v| (v - m).powi(2)).sum::<f64>() / (e.len() - 1) as f64).sqrt();
        println!(
            "{:>12} {:>+12.5} {:>12.5} {:>12.4}",
            name, m, sd, P1_PREDICTED[k]
        );
    }
    Ok(())
}

// ---------------------------------------------------------------------------
// the real measurement
// ---------------------------------------------------------------------------

/// Frame separations at which `rho(d)` is evaluated.
///
/// The all-pairs average that `cmd_rho` reports is the right statistic only if
/// every pair contributes equally. The merge does not work that way: it selects
/// the sharpest frames per pixel, and in a focus sweep those are *adjacent*.
/// If `rho(d)` decays with `d`, the merge sees the near-pair value, which is
/// larger, and the all-pairs average understates the floor.
const SEPS: &[usize] = &[1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96, 128];

/// Stride multiplier for the separation sweep, which must hold many warped
/// frames in memory at once.
const SEP_STRIDE_MULT: usize = 4;

/// Measure `rho` as a function of frame separation.
///
/// Holds every warped frame's lattice values (at a coarser stride) and then
/// forms the cross-covariance for each requested separation. The A/B
/// cross-estimate trick still does the work: only ever an A against a B, so
/// temporal noise cancels in numerator and denominator alike.
fn cmd_sep(
    edges: &Path,
    hp: usize,
    limit: Option<usize>,
    margin_override: Option<usize>,
) -> Result<()> {
    let mut pat = Pattern::load(hp)?;
    let tab = read_edges(edges)?;
    let n = limit.map_or(tab.n, |l| l.min(tab.n));
    println!(
        "=== sep: {} | {} frames | plane {}x{} | pattern A={} B={} hp={} px ===",
        tab.case, n, tab.geom.width, tab.geom.height, pat.n_a, pat.n_b, pat.hp
    );
    if pat.geom != tab.geom {
        pat = crop_pattern(&pat, tab.geom);
    }
    let margin = margin_override.unwrap_or(MARGIN_RADII * hp);

    for (solver, place) in placements(&tab) {
        let ts: Vec<Similarity> = place.iter().take(n).filter_map(|p| *p).collect();
        if ts.len() < 4 {
            continue;
        }
        println!("\n--- solver {solver}: {} frames placed ---", ts.len());
        let a = PlaneRef::from_geometry(&pat.a, tab.geom).expect("A");
        let b = PlaneRef::from_geometry(&pat.b, tab.geom).expect("B");
        let (cx, cy) = (tab.geom.width as f64 * 0.5, tab.geom.height as f64 * 0.5);

        for (name, r) in RESAMPLERS.iter() {
            // Same lattice rule as `cmd_rho`, coarser stride.
            let mut lat = lattice(tab.geom, &ts, *r, margin);
            let keep: Vec<usize> = (0..lat.xs.len()).step_by(SEP_STRIDE_MULT).collect();
            lat = Lattice {
                xs: keep.iter().map(|&i| lat.xs[i]).collect(),
                ys: keep.iter().map(|&i| lat.ys[i]).collect(),
                bin: keep.iter().map(|&i| lat.bin[i]).collect(),
            };
            let np = lat.xs.len();

            // Warp every frame once.
            let mut wa: Vec<Vec<f32>> = Vec::with_capacity(ts.len());
            let mut wb: Vec<Vec<f32>> = Vec::with_capacity(ts.len());
            for t in &ts {
                let mut va = vec![0f32; np];
                let mut vb = vec![0f32; np];
                for i in 0..np {
                    let (sx, sy) = t.apply_at(f64::from(lat.xs[i]), f64::from(lat.ys[i]), cx, cy);
                    va[i] = r.sample(a, sx, sy);
                    vb[i] = r.sample(b, sx, sy);
                }
                wa.push(va);
                wb.push(vb);
            }
            // Within-frame attenuation on the same points, as the normaliser.
            let mut c0 = Cov::default();
            for i in 0..np {
                let o = lat.ys[i] as usize * tab.geom.width + lat.xs[i] as usize;
                c0.push(f64::from(pat.a[o]), f64::from(pat.b[o]));
            }
            let c00 = c0.cov();
            let mut wsum = 0f64;
            for k in 0..ts.len() {
                let mut c = Cov::default();
                for i in 0..np {
                    c.push(f64::from(wa[k][i]), f64::from(wb[k][i]));
                }
                wsum += c.cov();
            }
            let w = wsum / ts.len() as f64 / c00;

            print!("{name:>12}  W={w:.4}  rho(d):");
            for &d in SEPS {
                if d >= ts.len() {
                    continue;
                }
                // Symmetrised: A_k against B_{k+d} and B_k against A_{k+d}.
                let mut c = Cov::default();
                for k in 0..(ts.len() - d) {
                    for i in 0..np {
                        c.push(f64::from(wa[k][i]), f64::from(wb[k + d][i]));
                        c.push(f64::from(wb[k][i]), f64::from(wa[k + d][i]));
                    }
                }
                print!(" {}:{:.4}", d, c.cov() / (w * c00));
            }
            println!();
        }
    }
    Ok(())
}

fn cmd_rho(
    edges: &Path,
    hp: usize,
    limit: Option<usize>,
    margin_override: Option<usize>,
) -> Result<()> {
    let mut pat = Pattern::load(hp)?;
    let tab = read_edges(edges)?;
    let n = limit.map_or(tab.n, |l| l.min(tab.n));
    println!(
        "=== rho: {} | {} frames | plane {}x{} | pattern A={} B={} hp={} px ===",
        tab.case, n, tab.geom.width, tab.geom.height, pat.n_a, pat.n_b, pat.hp
    );
    // The flats decode to a slightly wider active area than some stacks. Crop.
    //
    // This is safe *for this measurement specifically*: no scene data enters it,
    // so the pattern's absolute registration to a stack's photosites is never
    // used. All that is required is a field with the right spatial statistics
    // and the right amplitude, warped by the real measured transforms.
    if pat.geom != tab.geom {
        if pat.geom.width < tab.geom.width || pat.geom.height < tab.geom.height {
            bail!(
                "pattern plane {}x{} is smaller than the edge plane {}x{}",
                pat.geom.width,
                pat.geom.height,
                tab.geom.width,
                tab.geom.height
            );
        }
        println!(
            "  cropping pattern {}x{} -> {}x{} (no scene data enters, so registration is moot)",
            pat.geom.width, pat.geom.height, tab.geom.width, tab.geom.height
        );
        pat = crop_pattern(&pat, tab.geom);
    }
    let margin = margin_override.unwrap_or(MARGIN_RADII * hp);
    println!(
        "  interior margin {margin} px (default {MARGIN_RADII} x hp), so every window is fully interior"
    );
    println!(
        "  kappa(green luma) = {:.6}% whole plane, {:.6}% interior only",
        pat_kappa(&pat, 0) * 100.0,
        pat_kappa(&pat, margin) * 100.0
    );

    for (solver, place) in placements(&tab) {
        let ts: Vec<Similarity> = place.iter().take(n).filter_map(|p| *p).collect();
        if ts.len() < 2 {
            println!("\n  {solver}: placement not solvable");
            continue;
        }
        // How far does the warp actually move a photosite? This is the thing
        // that decides the answer, so it is reported before the answer.
        let (cx, cy) = (tab.geom.width as f64 * 0.5, tab.geom.height as f64 * 0.5);
        let corner = (cx * cx + cy * cy).sqrt();
        let mut d_centre = 0f64;
        let mut d_corner = 0f64;
        for w in ts.windows(2) {
            let (x0, y0) = w[0].apply_at(cx, cy, cx, cy);
            let (x1, y1) = w[1].apply_at(cx, cy, cx, cy);
            d_centre += ((x1 - x0).powi(2) + (y1 - y0).powi(2)).sqrt();
            let (a0, b0) = w[0].apply_at(0.0, 0.0, cx, cy);
            let (a1, b1) = w[1].apply_at(0.0, 0.0, cx, cy);
            d_corner += ((a1 - a0).powi(2) + (b1 - b0).powi(2)).sqrt();
        }
        let steps = (ts.len() - 1) as f64;
        println!(
            "\n--- solver {solver}: {} frames placed, corner radius {corner:.0} px ---",
            ts.len()
        );
        println!(
            "  mean adjacent-frame step: centre {:.4} px, corner {:.4} px",
            d_centre / steps,
            d_corner / steps
        );

        println!(
            "\n{:>12} {:>9} {:>9} {:>9} {:>10} {:>12}",
            "resampler", "W", "F", "n_prnu", "rho_warp", "points"
        );
        let mut per_res: Vec<(String, Merged)> = Vec::new();
        for (name, r) in RESAMPLERS.iter() {
            let lat = lattice(tab.geom, &ts, *r, margin);
            let m = merge_pattern(&pat.a, &pat.b, tab.geom, &ts, *r, &lat);
            println!(
                "{:>12} {:>9.4} {:>9.4} {:>9.3} {:>10.4} {:>12}",
                name,
                m.w_mean,
                m.f_all,
                1.0 / m.f_all,
                implied_rho(m.f_all, m.w_mean, ts.len()),
                m.points
            );
            per_res.push((name.to_string(), m));
        }

        println!("\n  radially resolved (fraction of corner radius), n_prnu:");
        print!("{:>12}", "bin");
        for b in 0..RADIAL_BINS {
            print!(
                "{:>9}",
                format!("{:.2}", (b as f64 + 0.5) / RADIAL_BINS as f64)
            );
        }
        println!();
        for (name, m) in &per_res {
            print!("{name:>12}");
            for b in 0..RADIAL_BINS {
                if m.n_bin[b] < 64 {
                    print!("{:>9}", "-");
                } else {
                    print!("{:>9.2}", 1.0 / m.f_bin[b]);
                }
            }
            println!();
        }
        println!("\n  radially resolved, F (1.000 = no averaging at all):");
        for (name, m) in &per_res {
            print!("{name:>12}");
            for b in 0..RADIAL_BINS {
                if m.n_bin[b] < 64 {
                    print!("{:>9}", "-");
                } else {
                    print!("{:>9.4}", m.f_bin[b]);
                }
            }
            println!();
        }
        println!("\n  radially resolved, W (within-frame attenuation):");
        for (name, m) in &per_res {
            print!("{name:>12}");
            for b in 0..RADIAL_BINS {
                if m.n_bin[b] < 64 {
                    print!("{:>9}", "-");
                } else {
                    print!("{:>9.4}", m.w_bin[b]);
                }
            }
            println!();
        }
        println!("\n  diagnostics: per-bin pattern variance / global, and point census");
        print!("{:>12}", "var ratio");
        for b in 0..RADIAL_BINS {
            print!("{:>9.3}", per_res[0].1.var_share[b]);
        }
        println!();
        print!("{:>12}", "points");
        for b in 0..RADIAL_BINS {
            print!("{:>9}", per_res[0].1.n_bin[b]);
        }
        println!();
        print!("{:>12}", "step px");
        for b in 0..RADIAL_BINS {
            let r = (b as f64 + 0.5) / RADIAL_BINS as f64;
            print!(
                "{:>9.3}",
                d_centre / steps + r * (d_corner - d_centre) / steps
            );
        }
        println!();

        // --- validity mask -------------------------------------------------
        //
        // `Nearest` cannot attenuate anything: it copies one photosite, so
        // W_Nearest is exactly 1 for any stationary field, whatever the warp.
        // Where it is not 1, the field in that bin is not stationary and the
        // ratio there is measuring the high-pass residual rather than PRNU.
        // This is an internal identity, not a fit to the answer.
        let keep: Vec<bool> = (0..RADIAL_BINS)
            .map(|b| {
                (per_res[0].1.w_bin[b] - 1.0).abs() <= W_NEAREST_TOL && per_res[0].1.n_bin[b] >= 64
            })
            .collect();
        let kept: Vec<String> = (0..RADIAL_BINS)
            .filter(|b| keep[*b])
            .map(|b| format!("{:.2}", (b as f64 + 0.5) / RADIAL_BINS as f64))
            .collect();
        println!(
            "\n  validity mask |W_Nearest - 1| <= {W_NEAREST_TOL}: bins kept = [{}]",
            kept.join(" ")
        );
        if kept.len() < 3 {
            println!("  WARNING: fewer than 3 bins survive; this stack is not measurable");
        }

        println!("\n  POOLED OVER VALID BINS ONLY:");
        println!(
            "{:>12} {:>9} {:>9} {:>9} {:>10} {:>12}",
            "resampler", "W", "F", "n_prnu", "rho_warp", "points"
        );
        let mut clean: Vec<(String, f64, f64)> = Vec::new();
        for (name, m) in &per_res {
            let (f, w, np) = m.pooled(&keep);
            println!(
                "{:>12} {:>9.4} {:>9.4} {:>9.3} {:>10.4} {:>12}",
                name,
                w,
                f,
                1.0 / f,
                implied_rho(f, w, ts.len()),
                np
            );
            clean.push((name.clone(), f, w));
        }

        // What it costs. predicted_sigma divides the temporal part by sqrt(n)
        // but the fixed pattern only falls to sqrt(F).
        println!("\n  sigma correction vs the two bounds, CatmullRom (the merge default):");
        let (cf, _, _) = per_res[2].1.pooled(&keep);
        let nf = ts.len() as f64;
        println!(
            "{:>16} {:>14} {:>14} {:>14}",
            "quantity", "F=1 (round 1)", "measured", "F=1/n"
        );
        println!("{:>16} {:>14.4} {:>14.4} {:>14.4}", "F", 1.0, cf, 1.0 / nf);
        println!(
            "{:>16} {:>14.3} {:>14.3} {:>14.3}",
            "n_prnu",
            1.0,
            1.0 / cf,
            nf
        );
        println!(
            "{:>16} {:>14.4} {:>14.4} {:>14.4}",
            "sigma_prnu/kS",
            1.0,
            cf.sqrt(),
            (1.0 / nf).sqrt()
        );
        println!(
            "{:>16} {:>14.2} {:>14.2} {:>14.2}",
            "vs round 1 (x)",
            1.0,
            cf.sqrt(),
            (1.0 / nf).sqrt()
        );
        println!(
            "  ROUND 1 OVERSTATED THE PRNU SIGMA BY {:.2}x ON THIS STACK",
            1.0 / cf.sqrt()
        );
    }
    Ok(())
}

/// Cross-estimate `kappa` on the interior only.
///
/// The whole-plane figure is not comparable with M71's: `box_mean` is
/// edge-clamped, so a border of width ~`hp` carries illumination curvature that
/// grows with the radius, and including it makes `kappa` look radius-dependent
/// when the underlying pattern is white.
fn pat_kappa(p: &Pattern, margin: usize) -> f64 {
    let mut c = Cov::default();
    let mut i = 0usize;
    for y in margin..p.geom.height.saturating_sub(margin) {
        for x in margin..p.geom.width.saturating_sub(margin) {
            i += 1;
            if i % 7 != 0 {
                continue;
            }
            let o = y * p.geom.width + x;
            c.push(f64::from(p.a[o]), f64::from(p.b[o]));
        }
    }
    c.cov().max(0.0).sqrt()
}

fn crop_pattern(p: &Pattern, to: PlaneGeometry) -> Pattern {
    let mut a = Vec::with_capacity(to.pixels());
    let mut b = Vec::with_capacity(to.pixels());
    for y in 0..to.height {
        let o = y * p.geom.width;
        a.extend_from_slice(&p.a[o..o + to.width]);
        b.extend_from_slice(&p.b[o..o + to.width]);
    }
    Pattern {
        geom: to,
        a,
        b,
        n_a: p.n_a,
        n_b: p.n_b,
        hp: p.hp,
    }
}

// ---------------------------------------------------------------------------

fn main() -> Result<()> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.is_empty() {
        bail!("usage: m90-rho <prnu|rho|control> [options]");
    }
    let mut hp = HP_RADIUS;
    let mut flats: Option<PathBuf> = None;
    let mut edges: Option<PathBuf> = None;
    let mut limit: Option<usize> = None;
    let mut margin: Option<usize> = None;
    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--hp" => {
                hp = args[i + 1].parse()?;
                i += 2;
            }
            "--flats" => {
                flats = Some(PathBuf::from(&args[i + 1]));
                i += 2;
            }
            "--edges" => {
                edges = Some(PathBuf::from(&args[i + 1]));
                i += 2;
            }
            "--limit" => {
                limit = Some(args[i + 1].parse()?);
                i += 2;
            }
            "--margin" => {
                margin = Some(args[i + 1].parse()?);
                i += 2;
            }
            other => bail!("unknown option {other}"),
        }
    }
    match args[0].as_str() {
        "prnu" => cmd_prnu(&flats.context("prnu needs --flats <DIR>")?, hp),
        "rho" => cmd_rho(
            &edges.context("rho needs --edges <CSV>")?,
            hp,
            limit,
            margin,
        ),
        "sep" => cmd_sep(
            &edges.context("sep needs --edges <CSV>")?,
            hp,
            limit,
            margin,
        ),
        "control" => cmd_control(),
        other => bail!("unknown subcommand {other}"),
    }
}
