//! Pure statistics for the FPN experiment.
//!
//! Nothing here does I/O, so every estimator can be checked against synthetic
//! data with known planted parameters. That matters more than usual: a prior
//! claim in this project was retracted because a *spatial* sd computed inside a
//! patch was reported as a *temporal* sd across frames. The two are computed by
//! separate functions here, named `spatial_*` and `temporal_*`, and
//! `spatial_and_temporal_measure_different_things` is the regression test.
//!
//! Dark frames sit at the black level (~512 DN) and roughly half of every
//! pixel's deviations are negative. Everything below is f64 and nothing is
//! clamped; black is never subtracted before a variance is taken.

/// splitmix64. Deterministic, seeded, no dependency.
pub struct Rng(u64);

impl Rng {
    pub fn new(seed: u64) -> Self {
        Rng(seed)
    }

    pub fn next_u64(&mut self) -> u64 {
        self.0 = self.0.wrapping_add(0x9E37_79B9_7F4A_7C15);
        let mut z = self.0;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        z ^ (z >> 31)
    }

    pub fn uniform(&mut self) -> f64 {
        (self.next_u64() >> 11) as f64 / (1u64 << 53) as f64
    }

    /// Box-Muller. Discards the sine term; we are not short of samples.
    pub fn normal(&mut self) -> f64 {
        let u1 = self.uniform().max(1e-300);
        let u2 = self.uniform();
        (-2.0 * u1.ln()).sqrt() * (std::f64::consts::TAU * u2).cos()
    }

    /// `k` distinct values from `0..n`, Fisher-Yates on a scratch permutation.
    pub fn sample_without_replacement(&mut self, n: usize, k: usize) -> Vec<usize> {
        let mut idx: Vec<usize> = (0..n).collect();
        for i in 0..k.min(n) {
            let j = i + (self.next_u64() as usize) % (n - i);
            idx.swap(i, j);
        }
        idx.truncate(k.min(n));
        idx
    }
}

/// Sample mean and sample sd (n-1). Two-pass, so no catastrophic cancellation
/// when the mean (~512) dwarfs the spread (~2).
pub fn mean_sd(v: &[f64]) -> (f64, f64) {
    let n = v.len();
    if n < 2 {
        return (v.first().copied().unwrap_or(0.0), 0.0);
    }
    let mean = v.iter().sum::<f64>() / n as f64;
    let ss: f64 = v.iter().map(|x| (x - mean) * (x - mean)).sum();
    (mean, (ss / (n - 1) as f64).sqrt())
}

/// Spatial spread: how much pixels differ from *each other* within one image.
pub fn spatial_mean_sd(image: &[f64]) -> (f64, f64) {
    use rayon::prelude::*;
    let n = image.len();
    if n < 2 {
        return (image.first().copied().unwrap_or(0.0), 0.0);
    }
    let mean = image.par_iter().sum::<f64>() / n as f64;
    let ss: f64 = image.par_iter().map(|x| (x - mean) * (x - mean)).sum();
    (mean, (ss / (n - 1) as f64).sqrt())
}

/// Temporal spread: how much one pixel differs from *itself* across frames.
pub struct TemporalStats {
    /// Per-pixel mean across the frames. Carries FPN plus `var_pooled / n` of
    /// residual temporal noise -- see [`fpn_bias_corrected`].
    pub means: Vec<f64>,
    /// Mean over pixels of the per-pixel sample variance. Pooling variances
    /// (not sds) is what makes this an unbiased estimate of sigma_temporal^2.
    pub var_pooled: f64,
    /// Mean over pixels of the per-pixel sample *sd*. Reported only because the
    /// spec asked for "sd then averaged"; it is biased low by the chi
    /// distribution and `var_pooled.sqrt()` is the number to quote.
    pub mean_of_sd: f64,
    pub frames: usize,
}

impl TemporalStats {
    pub fn sigma(&self) -> f64 {
        self.var_pooled.sqrt()
    }
}

/// Per-pixel statistics across frames. `frames` must all be the same length.
///
/// Chunked over pixels with the frames streamed inside each chunk. The obvious
/// pixel-major loop reads one pixel from each of 20 separate 16 MB
/// allocations before moving on, which misses cache on essentially every
/// access; this ordering keeps the whole chunk resident instead.
pub fn temporal_stats(frames: &[&[u16]]) -> TemporalStats {
    use rayon::prelude::*;

    let n = frames.len();
    let px = frames.first().map(|f| f.len()).unwrap_or(0);
    assert!(n >= 2, "temporal statistics need at least two frames");
    assert!(
        frames.iter().all(|f| f.len() == px),
        "frames differ in length"
    );

    // 20 frames x 64 Ki pixels x 2 B = 2.5 MB of frame data per chunk, which
    // stays resident while the chunk is reduced.
    const CHUNK: usize = 1 << 16;

    let mut means = vec![0.0f64; px];
    let (sum_var, sum_sd) = means
        .par_chunks_mut(CHUNK)
        .enumerate()
        .map(|(ci, out)| {
            let lo = ci * CHUNK;
            let hi = lo + out.len();
            for f in frames {
                let src = &f[lo..hi];
                for (o, &v) in out.iter_mut().zip(src) {
                    *o += v as f64;
                }
            }
            let inv = 1.0 / n as f64;
            for o in out.iter_mut() {
                *o *= inv;
            }
            let mut ss = vec![0.0f64; out.len()];
            for f in frames {
                let src = &f[lo..hi];
                for ((s, &v), &m) in ss.iter_mut().zip(src).zip(out.iter()) {
                    let d = v as f64 - m;
                    *s += d * d;
                }
            }
            let denom = (n - 1) as f64;
            let mut sv = 0.0f64;
            let mut sd = 0.0f64;
            for s in &ss {
                let var = s / denom;
                sv += var;
                sd += var.sqrt();
            }
            (sv, sd)
        })
        .reduce(|| (0.0, 0.0), |a, b| (a.0 + b.0, a.1 + b.1));

    TemporalStats {
        means,
        var_pooled: sum_var / px as f64,
        mean_of_sd: sum_sd / px as f64,
        frames: n,
    }
}

/// Fixed-pattern noise, corrected for the temporal noise still riding on the
/// per-pixel temporal means.
///
/// `var(means) = sigma_FPN^2 + sigma_temporal^2 / n`, so the second term must
/// come off. Skipping this is the single easiest way to report a fixed-pattern
/// floor that is really just under-averaged shot noise.
pub struct FpnEstimate {
    /// Raw spatial variance of the per-pixel temporal means -- biased high.
    pub raw_var: f64,
    /// The amount subtracted: `sigma_temporal^2 / n`.
    pub bias: f64,
    /// `raw_var - bias`. Negative means FPN is below what n frames can resolve.
    pub corrected_var: f64,
    /// `None` when `corrected_var` is negative: report "below resolution",
    /// never a small positive number obtained by clamping.
    pub sigma_fpn: Option<f64>,
}

pub fn fpn_bias_corrected(means: &[f64], var_temporal_pooled: f64, n: usize) -> FpnEstimate {
    let (_, sd) = spatial_mean_sd(means);
    let raw_var = sd * sd;
    let bias = var_temporal_pooled / n as f64;
    let corrected_var = raw_var - bias;
    FpnEstimate {
        raw_var,
        bias,
        corrected_var,
        sigma_fpn: if corrected_var > 0.0 {
            Some(corrected_var.sqrt())
        } else {
            None
        },
    }
}

/// Per-pixel average of the frames named by `idx`.
pub fn average_subset(frames: &[&[u16]], idx: &[usize]) -> Vec<f64> {
    use rayon::prelude::*;
    const CHUNK: usize = 1 << 16;
    let px = frames[idx[0]].len();
    let inv = 1.0 / idx.len() as f64;
    let mut out = vec![0.0f64; px];
    out.par_chunks_mut(CHUNK).enumerate().for_each(|(ci, dst)| {
        let lo = ci * CHUNK;
        let hi = lo + dst.len();
        for &i in idx {
            for (o, &v) in dst.iter_mut().zip(&frames[i][lo..hi]) {
                *o += v as f64;
            }
        }
        for o in dst.iter_mut() {
            *o *= inv;
        }
    });
    out
}

pub fn subtract(a: &[f64], b: &[f64]) -> Vec<f64> {
    a.iter().zip(b).map(|(x, y)| x - y).collect()
}

/// Split `0..n` into `n / size` disjoint blocks of `size`. Any remainder is
/// dropped rather than folded into the last block, so every subset has the
/// same N and the sigma-vs-N curve compares like with like.
pub fn disjoint_subsets(n: usize, size: usize) -> Vec<Vec<usize>> {
    (0..n / size)
        .map(|b| (b * size..(b + 1) * size).collect())
        .collect()
}

/// One point on a sigma-vs-N curve.
pub struct CurvePoint {
    pub n: usize,
    pub sd: f64,
    /// Spread across the subsets averaged at this N. Zero when there was only
    /// one subset. This is what a claimed departure from -0.5 must beat.
    pub scatter: f64,
    pub subsets: usize,
    /// False when the subsets had to overlap because the frame count could not
    /// supply two disjoint draws of this size.
    pub disjoint: bool,
}

/// Subsets of size `n` to average at one point of the curve, and whether they
/// are disjoint.
pub fn subsets_for(n_frames: usize, n: usize, rng: &mut Rng) -> (Vec<Vec<usize>>, bool) {
    if n == n_frames {
        return (vec![(0..n_frames).collect()], true);
    }
    let d = disjoint_subsets(n_frames, n);
    if d.len() >= 2 {
        return (d, true);
    }
    // Too few frames for two disjoint draws: fall back to overlapping random
    // draws so the point still has a scatter, and flag that they overlap.
    let v = (0..4)
        .map(|_| rng.sample_without_replacement(n_frames, n))
        .collect();
    (v, false)
}

fn curve_point(n: usize, sds: Vec<f64>, disjoint: bool) -> CurvePoint {
    let (m, sc) = if sds.len() >= 2 {
        mean_sd(&sds)
    } else {
        (sds[0], 0.0)
    };
    CurvePoint {
        n,
        sd: m,
        scatter: sc,
        subsets: sds.len(),
        disjoint,
    }
}

/// Spatial sd of the N-frame average, for each N in `ns`, averaged over several
/// subsets so no point rests on one draw's luck.
pub fn sigma_vs_n_curve(frames: &[&[u16]], ns: &[usize], rng: &mut Rng) -> Vec<CurvePoint> {
    use rayon::prelude::*;
    ns.iter()
        .map(|&k| {
            let (subs, disjoint) = subsets_for(frames.len(), k, rng);
            let sds: Vec<f64> = subs
                .par_iter()
                .map(|s| spatial_mean_sd(&average_subset(frames, s)).1)
                .collect();
            curve_point(k, sds, disjoint)
        })
        .collect()
}

/// The same curve with `master` subtracted from every average.
///
/// Subsets are drawn only from `frames[half..]`, so a master built from
/// `frames[..half]` never shares a frame with the thing it corrects. Passing a
/// master that overlaps the second half would subtract those frames' own
/// temporal noise and manufacture a result.
pub fn sigma_vs_n_bias_subtracted(
    frames: &[&[u16]],
    ns: &[usize],
    master: &[f64],
    half: usize,
) -> Vec<CurvePoint> {
    use rayon::prelude::*;
    let avail = frames.len() - half;
    ns.iter()
        .filter(|&&k| k <= avail)
        .map(|&k| {
            let sds: Vec<f64> = disjoint_subsets(avail, k)
                .par_iter()
                .map(|s| {
                    let abs: Vec<usize> = s.iter().map(|&i| i + half).collect();
                    spatial_mean_sd(&subtract(&average_subset(frames, &abs), master)).1
                })
                .collect();
            curve_point(k, sds, true)
        })
        .collect()
}

/// Least-squares fit of `log10(y) = slope * log10(x) + intercept`.
pub fn loglog_fit(points: &[(f64, f64)]) -> (f64, f64) {
    let n = points.len() as f64;
    let xs: Vec<f64> = points.iter().map(|p| p.0.log10()).collect();
    let ys: Vec<f64> = points.iter().map(|p| p.1.log10()).collect();
    let mx = xs.iter().sum::<f64>() / n;
    let my = ys.iter().sum::<f64>() / n;
    let num: f64 = xs.iter().zip(&ys).map(|(x, y)| (x - mx) * (y - my)).sum();
    let den: f64 = xs.iter().map(|x| (x - mx) * (x - mx)).sum();
    let slope = if den == 0.0 { 0.0 } else { num / den };
    (slope, my - slope * mx)
}

/// Median and median-absolute-deviation scaled to a Gaussian sd.
///
/// Used for the hot-pixel threshold: hot pixels are exactly the outliers a
/// mean-and-sd estimate would be dragged by, so the threshold has to come from
/// a robust estimator or it moves with the thing it is trying to detect.
///
/// On inputs above `SUBSAMPLE_ABOVE` this works from a strided subsample. A
/// median from 1 M+ samples is indistinguishable from one over 8 M, and the
/// stride is coprime with the row pitch so it cannot lock onto a column.
pub fn median_and_robust_sd(v: &[f64]) -> (f64, f64) {
    const SUBSAMPLE_ABOVE: usize = 2_000_000;
    const STRIDE: usize = 7;
    let mut s: Vec<f64> = if v.len() > SUBSAMPLE_ABOVE {
        v.iter().step_by(STRIDE).copied().collect()
    } else {
        v.to_vec()
    };
    s.sort_unstable_by(|a, b| a.partial_cmp(b).unwrap());
    let med = quantile_sorted(&s, 0.5);
    let mut dev: Vec<f64> = s.iter().map(|x| (x - med).abs()).collect();
    dev.sort_unstable_by(|a, b| a.partial_cmp(b).unwrap());
    (med, 1.4826 * quantile_sorted(&dev, 0.5))
}

fn quantile_sorted(sorted: &[f64], q: f64) -> f64 {
    if sorted.is_empty() {
        return 0.0;
    }
    let i = ((sorted.len() - 1) as f64 * q).round() as usize;
    sorted[i]
}

/// Exact quantile of u16 samples via a full 65536-bin histogram. Avoids sorting
/// 33 M values and is exact rather than interpolated.
pub struct U16Histogram {
    bins: Vec<u64>,
    count: u64,
}

impl Default for U16Histogram {
    fn default() -> Self {
        Self::new()
    }
}

impl U16Histogram {
    pub fn new() -> Self {
        U16Histogram {
            bins: vec![0; 1 << 16],
            count: 0,
        }
    }

    pub fn add(&mut self, v: u16) {
        self.bins[v as usize] += 1;
        self.count += 1;
    }

    pub fn extend(&mut self, vs: &[u16]) {
        for &v in vs {
            self.add(v);
        }
    }

    pub fn merge(&mut self, other: &U16Histogram) {
        for (a, b) in self.bins.iter_mut().zip(&other.bins) {
            *a += b;
        }
        self.count += other.count;
    }

    pub fn count(&self) -> u64 {
        self.count
    }

    pub fn min(&self) -> u16 {
        self.bins.iter().position(|&c| c > 0).unwrap_or(0) as u16
    }

    pub fn max(&self) -> u16 {
        self.bins.iter().rposition(|&c| c > 0).unwrap_or(0) as u16
    }

    /// Smallest value at or below which at least `q` of the mass lies.
    pub fn quantile(&self, q: f64) -> u16 {
        if self.count == 0 {
            return 0;
        }
        let target = (q * self.count as f64).ceil().max(1.0) as u64;
        let mut acc = 0u64;
        for (v, &c) in self.bins.iter().enumerate() {
            acc += c;
            if acc >= target {
                return v as u16;
            }
        }
        self.max()
    }

    pub fn mean(&self) -> f64 {
        if self.count == 0 {
            return 0.0;
        }
        let s: f64 = self
            .bins
            .iter()
            .enumerate()
            .map(|(v, &c)| v as f64 * c as f64)
            .sum();
        s / self.count as f64
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Build `n` frames of `px` pixels with a known fixed pattern and known
    /// independent temporal noise on top.
    fn planted(
        px: usize,
        n: usize,
        sigma_fpn: f64,
        sigma_t: f64,
        seed: u64,
    ) -> (Vec<Vec<u16>>, f64) {
        let mut rng = Rng::new(seed);
        let base = 512.0;
        let fpn: Vec<f64> = (0..px).map(|_| sigma_fpn * rng.normal()).collect();
        let frames: Vec<Vec<u16>> = (0..n)
            .map(|_| {
                fpn.iter()
                    .map(|f| {
                        (base + f + sigma_t * rng.normal())
                            .round()
                            .clamp(0.0, 65535.0) as u16
                    })
                    .collect()
            })
            .collect();
        (frames, base)
    }

    fn refs(frames: &[Vec<u16>]) -> Vec<&[u16]> {
        frames.iter().map(|f| f.as_slice()).collect()
    }

    #[test]
    fn fpn_estimator_recovers_planted_values() {
        let (frames, _) = planted(400_000, 20, 3.0, 8.0, 0xC0FFEE);
        let r = refs(&frames);
        let t = temporal_stats(&r);
        let f = fpn_bias_corrected(&t.means, t.var_pooled, t.frames);

        // Temporal sigma: planted 8.0, plus ~0.29 from rounding to integers.
        assert!(
            (t.sigma() - 8.0).abs() < 0.05,
            "sigma_temporal {} != 8.0",
            t.sigma()
        );
        let got = f.sigma_fpn.expect("planted FPN must be resolvable");
        assert!((got - 3.0).abs() < 0.05, "sigma_fpn {got} != 3.0");
    }

    #[test]
    fn the_bias_correction_is_what_makes_it_work() {
        // Without subtracting sigma_t^2/n the estimate is visibly too big:
        // sqrt(3^2 + 8^2/20) = 3.48 against a planted 3.0.
        let (frames, _) = planted(400_000, 20, 3.0, 8.0, 7);
        let r = refs(&frames);
        let t = temporal_stats(&r);
        let f = fpn_bias_corrected(&t.means, t.var_pooled, t.frames);
        let uncorrected = f.raw_var.sqrt();
        assert!(
            (uncorrected - 3.48).abs() < 0.05,
            "uncorrected {uncorrected} should sit near 3.48"
        );
        assert!(uncorrected - f.sigma_fpn.unwrap() > 0.4);
    }

    #[test]
    fn zero_fpn_is_reported_as_below_resolution_not_as_a_small_number() {
        let (frames, _) = planted(400_000, 20, 0.0, 8.0, 99);
        let r = refs(&frames);
        let t = temporal_stats(&r);
        let f = fpn_bias_corrected(&t.means, t.var_pooled, t.frames);
        // corrected_var straddles zero; either outcome is honest, but a large
        // positive sigma would mean the correction failed.
        match f.sigma_fpn {
            None => {}
            Some(s) => assert!(s < 0.35, "planted zero FPN reported as {s}"),
        }
    }

    #[test]
    fn spatial_and_temporal_measure_different_things() {
        // A strong fixed pattern with almost no temporal noise: spatial sd is
        // large, temporal sd is tiny. Conflating them was a retracted claim.
        let (frames, _) = planted(200_000, 20, 40.0, 0.5, 4242);
        let r = refs(&frames);
        let t = temporal_stats(&r);
        let (_, spatial) = spatial_mean_sd(&average_subset(&r, &(0..20).collect::<Vec<_>>()));
        assert!(t.sigma() < 1.0, "temporal {} should be tiny", t.sigma());
        assert!(spatial > 30.0, "spatial {spatial} should be large");
        assert!(spatial / t.sigma() > 30.0);
    }

    #[test]
    fn averaging_independent_noise_follows_one_over_sqrt_n() {
        let (frames, _) = planted(200_000, 16, 0.0, 20.0, 5150);
        let r = refs(&frames);
        let mut pts = Vec::new();
        for n in [1usize, 2, 4, 8, 16] {
            let subs = disjoint_subsets(16, n);
            let sd: f64 = subs
                .iter()
                .map(|s| spatial_mean_sd(&average_subset(&r, s)).1)
                .sum::<f64>()
                / subs.len() as f64;
            pts.push((n as f64, sd));
        }
        let (slope, _) = loglog_fit(&pts);
        assert!(
            (slope + 0.5).abs() < 0.02,
            "pure temporal noise must fall as -0.5, got {slope}"
        );
    }

    #[test]
    fn averaging_a_fixed_pattern_asymptotes_instead() {
        let (frames, _) = planted(200_000, 16, 10.0, 20.0, 1234);
        let r = refs(&frames);
        let sd_at = |n: usize| {
            let subs = disjoint_subsets(16, n);
            subs.iter()
                .map(|s| spatial_mean_sd(&average_subset(&r, s)).1)
                .sum::<f64>()
                / subs.len() as f64
        };
        let (s1, s16) = (sd_at(1), sd_at(16));
        // sqrt(10^2 + 20^2/16) = 11.18, not 22.4/4 = 5.6.
        assert!((s16 - 11.18).abs() < 0.3, "N=16 sd {s16} != 11.18");
        assert!(s1 / s16 < 2.4, "an asymptoting curve cannot fall 4x");
    }

    #[test]
    fn disjoint_subsets_do_not_share_frames() {
        let subs = disjoint_subsets(20, 6);
        assert_eq!(subs.len(), 3);
        assert!(subs.iter().all(|s| s.len() == 6));
        let mut seen = std::collections::HashSet::new();
        for s in &subs {
            for &i in s {
                assert!(seen.insert(i), "frame {i} reused across subsets");
            }
        }
        // 20 / 6 = 3 blocks, remainder dropped rather than making a short block.
        assert_eq!(seen.len(), 18);
    }

    #[test]
    fn loglog_fit_recovers_a_known_slope() {
        let pts: Vec<(f64, f64)> = (1..=10)
            .map(|n| (n as f64, 7.0 * (n as f64).powf(-0.5)))
            .collect();
        let (slope, intercept) = loglog_fit(&pts);
        assert!((slope + 0.5).abs() < 1e-9);
        assert!((10f64.powf(intercept) - 7.0).abs() < 1e-9);
    }

    #[test]
    fn average_subset_is_the_arithmetic_mean() {
        let a: Vec<u16> = vec![10, 20, 30];
        let b: Vec<u16> = vec![20, 30, 40];
        let f = vec![a.as_slice(), b.as_slice()];
        assert_eq!(average_subset(&f, &[0, 1]), vec![15.0, 25.0, 35.0]);
        assert_eq!(average_subset(&f, &[1]), vec![20.0, 30.0, 40.0]);
    }

    #[test]
    fn histogram_quantiles_match_a_sorted_reference() {
        let mut rng = Rng::new(11);
        let vals: Vec<u16> = (0..50_000)
            .map(|_| (512.0 + 10.0 * rng.normal()).round().clamp(0.0, 65535.0) as u16)
            .collect();
        let mut h = U16Histogram::new();
        h.extend(&vals);
        let mut sorted = vals.clone();
        sorted.sort_unstable();
        for q in [0.001, 0.5, 0.99, 0.9999] {
            let want = sorted[((q * sorted.len() as f64).ceil().max(1.0) as usize) - 1];
            assert_eq!(h.quantile(q), want, "quantile {q}");
        }
        assert_eq!(h.min(), *sorted.first().unwrap());
        assert_eq!(h.max(), *sorted.last().unwrap());
        assert!((h.mean() - 512.0).abs() < 0.2);
    }

    #[test]
    fn histograms_merge_additively() {
        let mut a = U16Histogram::new();
        a.extend(&[1, 2, 3]);
        let mut b = U16Histogram::new();
        b.extend(&[4, 5]);
        a.merge(&b);
        assert_eq!(a.count(), 5);
        assert_eq!(a.min(), 1);
        assert_eq!(a.max(), 5);
        assert!((a.mean() - 3.0).abs() < 1e-12);
    }

    #[test]
    fn robust_sd_ignores_the_outliers_it_is_used_to_find() {
        let mut rng = Rng::new(808);
        let mut v: Vec<f64> = (0..20_000).map(|_| 512.0 + 4.0 * rng.normal()).collect();
        let (_, clean) = median_and_robust_sd(&v);
        for i in 0..200 {
            v[i * 97] = 5000.0; // hot pixels
        }
        let (med, robust) = median_and_robust_sd(&v);
        let (_, naive) = mean_sd(&v);
        assert!((med - 512.0).abs() < 0.3);
        assert!(
            (robust - clean).abs() < 0.2,
            "robust sd moved: {clean} -> {robust}"
        );
        assert!(
            naive > 5.0 * robust,
            "the naive sd should be wrecked by the outliers"
        );
    }

    #[test]
    fn sampling_without_replacement_returns_distinct_indices() {
        let mut rng = Rng::new(3);
        for _ in 0..50 {
            let s = rng.sample_without_replacement(20, 12);
            assert_eq!(s.len(), 12);
            let uniq: std::collections::HashSet<_> = s.iter().collect();
            assert_eq!(uniq.len(), 12);
            assert!(s.iter().all(|&i| i < 20));
        }
    }

    #[test]
    fn subtract_is_elementwise() {
        assert_eq!(subtract(&[5.0, 7.0], &[1.0, 2.0]), vec![4.0, 5.0]);
    }

    /// Rule 11: the headline number needs a test on its own code path. The next
    /// four call `sigma_vs_n_curve` and `sigma_vs_n_bias_subtracted` — the same
    /// functions `analyse_plane` calls — on frames with planted FPN and
    /// temporal noise, and check the reported slope and asymptote are the
    /// planted ones.
    fn planted_frames(
        px: usize,
        n: usize,
        sigma_fpn: f64,
        sigma_t: f64,
        seed: u64,
    ) -> Vec<Vec<u16>> {
        let mut rng = Rng::new(seed);
        let fpn: Vec<f64> = (0..px).map(|_| rng.normal() * sigma_fpn).collect();
        (0..n)
            .map(|_| {
                fpn.iter()
                    .map(|f| (2000.0 + f + rng.normal() * sigma_t).round().max(0.0) as u16)
                    .collect()
            })
            .collect()
    }

    #[test]
    fn the_production_curve_reports_the_planted_slope_and_asymptote() {
        let (px, n, sigma_fpn, sigma_t) = (300_000usize, 20usize, 3.0f64, 8.0f64);
        let frames = planted_frames(px, n, sigma_fpn, sigma_t, 0xC0FFEE);
        let refs: Vec<&[u16]> = frames.iter().map(|f| f.as_slice()).collect();
        let mut rng = Rng::new(7);
        let curve = sigma_vs_n_curve(&refs, &[1, 2, 4, 8, 20], &mut rng);

        // Every point must match sqrt(FPN^2 + sigma_t^2/N), the model M4 claims
        // the curve follows.
        for c in &curve {
            let expect = (sigma_fpn * sigma_fpn + sigma_t * sigma_t / c.n as f64).sqrt();
            assert!(
                (c.sd - expect).abs() < 0.12,
                "N={}: curve gave {:.4}, model predicts {expect:.4}",
                c.n,
                c.sd
            );
        }
        let pts: Vec<(f64, f64)> = curve.iter().map(|c| (c.n as f64, c.sd)).collect();
        let (slope, _) = loglog_fit(&pts);
        assert!(
            slope > -0.45 && slope < -0.2,
            "planted FPN should flatten the slope, got {slope:.4}"
        );
        let last = curve.last().unwrap();
        // The N=20 point is *not* the asymptote -- it still carries
        // sigma_t^2/20. Removing that recovers the planted FPN, which is what
        // "the curve asymptotes at sigma_FPN" actually means.
        let deconvolved = (last.sd * last.sd - sigma_t * sigma_t / last.n as f64).sqrt();
        assert!(
            (deconvolved - sigma_fpn).abs() < 0.05,
            "asymptote should be the planted FPN {sigma_fpn:.2}, got {deconvolved:.4} \
             (raw last point {:.4}, which still holds sigma_t^2/{})",
            last.sd,
            last.n
        );
    }

    #[test]
    fn the_production_curve_gives_minus_half_when_no_fpn_is_planted() {
        let frames = planted_frames(300_000, 20, 0.0, 8.0, 0xBEEF);
        let refs: Vec<&[u16]> = frames.iter().map(|f| f.as_slice()).collect();
        let mut rng = Rng::new(7);
        let curve = sigma_vs_n_curve(&refs, &[1, 2, 4, 8, 20], &mut rng);
        let pts: Vec<(f64, f64)> = curve.iter().map(|c| (c.n as f64, c.sd)).collect();
        let (slope, _) = loglog_fit(&pts);
        assert!(
            (slope + 0.5).abs() < 0.02,
            "with no FPN the production curve must give -0.5, got {slope:.4}"
        );
    }

    /// The M4 headline: subtracting a disjoint master restores -0.5 on the very
    /// same frames whose raw curve asymptotes. Both curves come from the
    /// production functions, so this fails if either regresses.
    #[test]
    fn the_production_bias_subtracted_curve_restores_minus_half() {
        let (n, sigma_fpn, sigma_t) = (20usize, 3.0f64, 8.0f64);
        let frames = planted_frames(300_000, n, sigma_fpn, sigma_t, 0xD00D);
        let refs: Vec<&[u16]> = frames.iter().map(|f| f.as_slice()).collect();
        let half = n / 2;
        let ns = [1usize, 2, 4, 8, 10];

        let mut rng = Rng::new(7);
        let raw = sigma_vs_n_curve(&refs, &ns, &mut rng);
        let (raw_slope, _) =
            loglog_fit(&raw.iter().map(|c| (c.n as f64, c.sd)).collect::<Vec<_>>());

        let master = average_subset(&refs, &(0..half).collect::<Vec<_>>());
        let corrected = sigma_vs_n_bias_subtracted(&refs, &ns, &master, half);
        // The master carries sigma_t^2/half of its own noise into every point.
        let master_noise_var = sigma_t * sigma_t / half as f64;
        let pts: Vec<(f64, f64)> = corrected
            .iter()
            .map(|c| (c.n as f64, (c.sd * c.sd - master_noise_var).max(0.0).sqrt()))
            .collect();
        let (slope, _) = loglog_fit(&pts);

        assert!(
            (slope + 0.5).abs() < 0.03,
            "bias-subtracted curve should be -0.5, got {slope:.4}"
        );
        assert!(
            raw_slope > slope + 0.15,
            "the whole M4 claim is that {raw_slope:.4} (raw) is visibly shallower than {slope:.4}"
        );
        assert!(
            corrected.iter().all(|c| c.disjoint && c.n <= half),
            "every corrected point must be disjoint from the master and fit in its half"
        );
    }

    #[test]
    fn subsets_are_flagged_when_they_have_to_overlap() {
        let mut rng = Rng::new(1);
        let (subs, disjoint) = subsets_for(20, 4, &mut rng);
        assert!(disjoint, "20 frames give 5 disjoint subsets of 4");
        assert_eq!(subs.len(), 5);

        let (subs, disjoint) = subsets_for(20, 12, &mut rng);
        assert!(
            !disjoint,
            "20 frames cannot give two disjoint subsets of 12"
        );
        assert!(
            subs.len() >= 2,
            "an overlapping fallback still needs scatter"
        );
        assert!(subs.iter().all(|s| s.len() == 12));

        let (subs, disjoint) = subsets_for(20, 20, &mut rng);
        assert!(disjoint, "the full set is trivially disjoint from nothing");
        assert_eq!(subs.len(), 1);
    }

    /// The split-half result the experiment reports rests on two claims: that
    /// subtracting a master bias built from *disjoint* frames removes the FPN
    /// and leaves `2*sigma_t^2/h`, and that using the *same* frames instead
    /// manufactures a fake floor. Plant known values and check both.
    #[test]
    fn split_half_removes_planted_fpn_and_self_correction_fakes_it() {
        let px = 200_000;
        let (n, sigma_fpn, sigma_t) = (20usize, 3.0f64, 8.0f64);
        let mut rng = Rng::new(0x5150);
        let fpn: Vec<f64> = (0..px).map(|_| rng.normal() * sigma_fpn).collect();
        let frames: Vec<Vec<u16>> = (0..n)
            .map(|_| {
                fpn.iter()
                    .map(|f| (2000.0 + f + rng.normal() * sigma_t).round().max(0.0) as u16)
                    .collect()
            })
            .collect();
        let refs: Vec<&[u16]> = frames.iter().map(|f| f.as_slice()).collect();
        let h = n / 2;
        let first: Vec<usize> = (0..h).collect();
        let second: Vec<usize> = (h..n).collect();

        let master = average_subset(&refs, &first);
        let target = average_subset(&refs, &second);

        // Disjoint: FPN goes, 2*sigma_t^2/h remains.
        let honest = spatial_mean_sd(&subtract(&target, &master)).1;
        let expected = (2.0 * sigma_t * sigma_t / h as f64).sqrt();
        assert!(
            (honest - expected).abs() < 0.1,
            "disjoint correction gave {honest:.4}, expected the temporal floor {expected:.4}"
        );

        // Self-corrected: the target's own noise cancels, leaving nothing.
        // This is the fake result the disjointness rule exists to prevent.
        let self_master = average_subset(&refs, &second);
        let fake = spatial_mean_sd(&subtract(&target, &self_master)).1;
        assert!(
            fake < 1e-9,
            "self-correction should collapse to zero, gave {fake:.6}"
        );
        assert!(
            fake < honest,
            "the fake result must look better than the honest one, or the test proves nothing"
        );
    }

    /// The corrected sigma-vs-N curve subtracts a master that carries
    /// `sigma_t^2/h` of its own noise. Removing that in quadrature must
    /// recover a clean -0.5 slope when the planted noise is independent.
    #[test]
    fn removing_the_masters_own_noise_recovers_the_half_power_slope() {
        let px = 120_000;
        let (n, sigma_fpn, sigma_t) = (20usize, 3.0f64, 8.0f64);
        let mut rng = Rng::new(0xA11CE);
        let fpn: Vec<f64> = (0..px).map(|_| rng.normal() * sigma_fpn).collect();
        let frames: Vec<Vec<u16>> = (0..n)
            .map(|_| {
                fpn.iter()
                    .map(|f| (2000.0 + f + rng.normal() * sigma_t).round().max(0.0) as u16)
                    .collect()
            })
            .collect();
        let refs: Vec<&[u16]> = frames.iter().map(|f| f.as_slice()).collect();
        let h = n / 2;
        let master = average_subset(&refs, &(0..h).collect::<Vec<_>>());
        let master_noise_var = sigma_t * sigma_t / h as f64;

        let pts: Vec<(f64, f64)> = [1usize, 2, 5, 10]
            .iter()
            .map(|&k| {
                let idx: Vec<usize> = (h..h + k).collect();
                let avg = average_subset(&refs, &idx);
                let sd = spatial_mean_sd(&subtract(&avg, &master)).1;
                (k as f64, (sd * sd - master_noise_var).max(0.0).sqrt())
            })
            .collect();
        let (slope, _) = loglog_fit(&pts);
        assert!(
            (slope + 0.5).abs() < 0.03,
            "expected -0.5 after deconvolving the master, got {slope:.4}"
        );

        // Without the correction the same frames asymptote, because the FPN
        // never averages away. This is the contrast the experiment reports.
        let raw: Vec<(f64, f64)> = [1usize, 2, 5, 10]
            .iter()
            .map(|&k| {
                let idx: Vec<usize> = (h..h + k).collect();
                (k as f64, spatial_mean_sd(&average_subset(&refs, &idx)).1)
            })
            .collect();
        let (raw_slope, _) = loglog_fit(&raw);
        assert!(
            raw_slope > slope + 0.05,
            "uncorrected slope {raw_slope:.4} should be visibly shallower than {slope:.4}"
        );
    }
}
