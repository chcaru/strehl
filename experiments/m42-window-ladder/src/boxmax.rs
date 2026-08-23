//! O(1)-per-pixel windowed **max**, and an exact windowed **percentile**.
//!
//! # Why this module exists
//!
//! `crates/strehl-core/src/boxfilter.rs` gives the shipped operator a windowed
//! *mean* by running sum, which is O(1) in the radius — SYNTHESIS fact 66, and
//! the reason M13's 27x27 window was free. The mean is also exactly why the
//! operator is blind on an untextured monotone edge (fact 73): the mean of
//! `|grad|` over a window wider than the blur is total variation / area, and
//! blur **conserves** total variation on a monotone edge.
//!
//! A windowed maximum is not TV-conserving — the peak gradient of a blurred
//! step falls like `1/sigma` — so it is the natural candidate for the missing
//! half of a dual response. This module supplies it at the same cost class.
//!
//! # The algorithm
//!
//! **van Herk (1992) / Gil & Werman (1993)**, the standard O(1) running
//! max/min: partition the line into blocks of the window length `k = 2r+1`,
//! precompute a within-block prefix max `S` and suffix max `P`, and read any
//! aligned window as `max(P[lo], S[hi])`. Three comparisons per element
//! regardless of `k`. The max is separable over a rectangle, so two 1-D passes
//! give the 2-D window.
//!
//! *(Textbook algorithm, described from the published papers. No GPL source was
//! opened; `AGENTS.md`'s licence discipline is unaffected.)*
//!
//! # Border policy: `-inf` padding, which IS `box_mean`'s clamped window
//!
//! `box_mean` intersects the window with the plane and divides by the surviving
//! count. For a maximum there is no divisor, so the identical policy — "take
//! the extremum over whatever part of the window is inside the plane" — is
//! obtained exactly by padding the line with `-inf` and running full windows.
//! That keeps the vHGW loop branch-free at the border and keeps the cost
//! genuinely independent of the radius there too, which a special-cased border
//! loop would not.
//!
//! The two filters therefore agree about *support* at every pixel, which is
//! what makes a `(mean, max)` dual well defined: both terms see the same set of
//! samples.

use strehl_core::plane::PlaneGeometry;

/// Reusable vHGW block arrays.
///
/// Hoisting these out of the call turned out to matter a great deal: with the
/// buffers allocated per call, `box_max` read 1.34 ms/frame/Mpx at radius 1 and
/// 6.61 at radius 40 with a 260% spread between passes, which looks exactly
/// like a radius-dependent algorithm and is not one — it is the allocator and
/// the page faults on a buffer whose size grows with `2r`. `box_mean` takes its
/// scratch from the caller, so a comparison against it is only fair if this
/// does too.
#[derive(Default)]
pub struct MaxScratch {
    prefix: Vec<f32>,
    suffix: Vec<f32>,
}

impl MaxScratch {
    fn ensure(&mut self, n: usize) {
        if self.prefix.len() < n {
            self.prefix.resize(n, f32::NEG_INFINITY);
            self.suffix.resize(n, f32::NEG_INFINITY);
        }
    }
}

/// Max of `src` over a `(2*radius+1)^2` window centred on each pixel, with the
/// window clamped to the plane.
///
/// `scratch` and `dst` must both be `geom.pixels()` long. `scratch` is
/// overwritten. Cost is O(1) per pixel in `radius`.
pub fn box_max(
    src: &[f32],
    geom: PlaneGeometry,
    radius: usize,
    scratch: &mut [f32],
    dst: &mut [f32],
) {
    let mut state = MaxScratch::default();
    box_max_with(&mut state, src, geom, radius, scratch, dst);
}

/// [`box_max`] with the vHGW block arrays supplied by the caller.
pub fn box_max_with(
    state: &mut MaxScratch,
    src: &[f32],
    geom: PlaneGeometry,
    radius: usize,
    scratch: &mut [f32],
    dst: &mut [f32],
) {
    let (w, h) = (geom.width, geom.height);
    assert_eq!(src.len(), geom.pixels());
    assert_eq!(scratch.len(), geom.pixels());
    assert_eq!(dst.len(), geom.pixels());
    if w == 0 || h == 0 {
        return;
    }
    if radius == 0 {
        dst.copy_from_slice(src);
        return;
    }
    state.ensure((w.max(h * CHUNK) + 2 * radius * CHUNK.max(1)).max((h + 2 * radius) * CHUNK));
    horizontal_max(state, src, w, h, radius, scratch);
    vertical_max(state, scratch, w, h, radius, dst);
}

/// vHGW over one padded line held in `prefix`/`suffix`.
///
/// `n` is the true line length, `r` the radius; both buffers must be
/// `n + 2*r` long and already hold the padded line (`-inf` in the `r` slots at
/// each end). On return `prefix[j]` is the max from its block's start to `j`
/// and `suffix[j]` the max from `j` to its block's end.
///
/// Iterated block by block rather than `if j % k == 0`, because a modulo by a
/// runtime `k` is an integer division per element and would put a term in the
/// inner loop that has nothing to do with the algorithm.
fn block_extrema(prefix: &mut [f32], suffix: &mut [f32], n: usize, r: usize) {
    let k = 2 * r + 1;
    let m = n + 2 * r;
    debug_assert_eq!(prefix.len(), m);
    debug_assert_eq!(suffix.len(), m);

    let mut b = 0;
    while b < m {
        let end = (b + k).min(m);
        for j in b + 1..end {
            prefix[j] = prefix[j].max(prefix[j - 1]);
        }
        for j in (b..end - 1).rev() {
            suffix[j] = suffix[j].max(suffix[j + 1]);
        }
        b += k;
    }
}

fn horizontal_max(
    state: &mut MaxScratch,
    src: &[f32],
    w: usize,
    h: usize,
    r: usize,
    dst: &mut [f32],
) {
    let m = w + 2 * r;
    let prefix = &mut state.prefix[..m];
    let suffix = &mut state.suffix[..m];
    for y in 0..h {
        let row = &src[y * w..(y + 1) * w];
        prefix[..r].fill(f32::NEG_INFINITY);
        prefix[r + w..].fill(f32::NEG_INFINITY);
        prefix[r..r + w].copy_from_slice(row);
        suffix.copy_from_slice(prefix);
        block_extrema(prefix, suffix, w, r);
        let out = &mut dst[y * w..(y + 1) * w];
        for (x, o) in out.iter_mut().enumerate() {
            // Original window [x-r, x+r] is padded window [x, x+2r].
            *o = suffix[x].max(prefix[x + 2 * r]);
        }
    }
}

const CHUNK: usize = 64;

/// Column pass, run in chunks of columns so the vHGW arrays stay in cache.
///
/// A running-sum vertical pass can be done row-wise with one accumulator per
/// column (that is what `box_mean` does), but a max has no inverse, so the
/// block arrays have to exist. Processing `CHUNK` columns at a time keeps the
/// access pattern row-major inside the chunk.
fn vertical_max(
    state: &mut MaxScratch,
    src: &[f32],
    w: usize,
    h: usize,
    r: usize,
    dst: &mut [f32],
) {
    let m = h + 2 * r;
    let k = 2 * r + 1;
    let prefix = &mut state.prefix[..m * CHUNK];
    let suffix = &mut state.suffix[..m * CHUNK];

    let mut c0 = 0;
    while c0 < w {
        let cw = CHUNK.min(w - c0);
        for j in 0..m {
            let dstrow = &mut prefix[j * CHUNK..j * CHUNK + cw];
            if j < r || j >= r + h {
                dstrow.fill(f32::NEG_INFINITY);
            } else {
                let y = j - r;
                dstrow.copy_from_slice(&src[y * w + c0..y * w + c0 + cw]);
            }
        }
        suffix.copy_from_slice(prefix);

        let mut b = 0;
        while b < m {
            let end = (b + k).min(m);
            for j in b + 1..end {
                let (lo, hi) = prefix.split_at_mut(j * CHUNK);
                let prev = &lo[(j - 1) * CHUNK..(j - 1) * CHUNK + cw];
                for (a, p) in hi[..cw].iter_mut().zip(prev) {
                    *a = a.max(*p);
                }
            }
            for j in (b..end - 1).rev() {
                let (lo, hi) = suffix.split_at_mut((j + 1) * CHUNK);
                let next = &hi[..cw];
                for (a, p) in lo[j * CHUNK..j * CHUNK + cw].iter_mut().zip(next) {
                    *a = a.max(*p);
                }
            }
            b += k;
        }

        for y in 0..h {
            let lo = &suffix[y * CHUNK..y * CHUNK + cw];
            let hi = &prefix[(y + 2 * r) * CHUNK..(y + 2 * r) * CHUNK + cw];
            let out = &mut dst[y * w + c0..y * w + c0 + cw];
            for ((o, a), b) in out.iter_mut().zip(lo).zip(hi) {
                *o = a.max(*b);
            }
        }
        c0 += cw;
    }
}

/// Exact `q`-quantile of `src` over a `(2*radius+1)^2` clamped window.
///
/// **This is NOT in the running filter's cost class and is not offered as
/// one.** It is a direct gather plus a partial selection, `O((2r+1)^2)` per
/// pixel, and it exists so the percentile arms of M17's candidate list can be
/// *measured*. A shippable constant-time percentile needs a sliding histogram;
/// none is built here, because the measurement decides whether one would ever
/// be worth building.
///
/// The rank convention is `floor(q * n)` clamped into `[0, n-1]` on the
/// ascending order of the `n` in-plane samples, so `q = 1.0` is exactly
/// [`box_max`] and `q = 0.0` is the window minimum.
pub fn window_percentile(src: &[f32], geom: PlaneGeometry, radius: usize, q: f32, dst: &mut [f32]) {
    let (w, h) = (geom.width, geom.height);
    assert_eq!(src.len(), geom.pixels());
    assert_eq!(dst.len(), geom.pixels());
    if w == 0 || h == 0 {
        return;
    }
    let mut buf: Vec<f32> = Vec::with_capacity((2 * radius + 1) * (2 * radius + 1));
    for y in 0..h {
        let y0 = y.saturating_sub(radius);
        let y1 = (y + radius).min(h - 1);
        for x in 0..w {
            let x0 = x.saturating_sub(radius);
            let x1 = (x + radius).min(w - 1);
            buf.clear();
            for yy in y0..=y1 {
                buf.extend_from_slice(&src[yy * w + x0..yy * w + x1 + 1]);
            }
            let n = buf.len();
            let idx = ((q * n as f32).floor() as usize).min(n - 1);
            let (_, v, _) = buf.select_nth_unstable_by(idx, |a, b| a.total_cmp(b));
            dst[y * w + x] = *v;
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Direct 2D gather with the same clamped-window rule. Deliberately naive,
    /// and deliberately the same shape as `boxfilter.rs`'s own `reference`.
    fn reference_max(src: &[f32], geom: PlaneGeometry, radius: usize) -> Vec<f32> {
        let (w, h) = (geom.width, geom.height);
        let mut out = vec![0.0f32; w * h];
        for y in 0..h {
            for x in 0..w {
                let x0 = x.saturating_sub(radius);
                let x1 = (x + radius).min(w - 1);
                let y0 = y.saturating_sub(radius);
                let y1 = (y + radius).min(h - 1);
                let mut best = f32::NEG_INFINITY;
                for yy in y0..=y1 {
                    for xx in x0..=x1 {
                        best = best.max(src[yy * w + xx]);
                    }
                }
                out[y * w + x] = best;
            }
        }
        out
    }

    fn run(w: usize, h: usize, radius: usize, sample: impl Fn(usize, usize) -> f32) {
        let geom = PlaneGeometry {
            width: w,
            height: h,
        };
        let src: Vec<f32> = (0..h)
            .flat_map(|y| (0..w).map(move |x| (x, y)))
            .map(|(x, y)| sample(x, y))
            .collect();
        let mut scratch = vec![0.0f32; geom.pixels()];
        let mut got = vec![0.0f32; geom.pixels()];
        box_max(&src, geom, radius, &mut scratch, &mut got);
        let want = reference_max(&src, geom, radius);
        // Exact: a max selects a sample, it does not accumulate one, so there
        // is no rounding to tolerate and any tolerance would hide a bug.
        for i in 0..geom.pixels() {
            assert_eq!(
                got[i], want[i],
                "w={w} h={h} r={radius} at {i}: got {} want {}",
                got[i], want[i]
            );
        }
    }

    /// GATE 2. The same shape as `boxfilter.rs::running_sums_match_the_naive_gather`,
    /// widened: more radii, more geometries, and a pseudorandom field as well as
    /// the lattice one, because a lattice can alias against a block size.
    #[test]
    fn running_max_matches_the_naive_gather() {
        let mut state = 0x2026_0823_u64;
        let mut rand = move || {
            state ^= state << 13;
            state ^= state >> 7;
            state ^= state << 17;
            ((state >> 11) as f64 / (1u64 << 53) as f64) as f32 * 2000.0 - 1000.0
        };
        for radius in [0usize, 1, 2, 3, 5, 8, 13, 21, 40] {
            for (w, h) in [
                (1, 1),
                (1, 9),
                (9, 1),
                (8, 5),
                (17, 13),
                (32, 4),
                (64, 3),
                (37, 41),
                (129, 67),
            ] {
                // Deterministic lattice, exactly boxfilter.rs's own sample.
                run(w, h, radius, |x, y| {
                    ((x * 7 + y * 13) % 19) as f32 * 3.5 - 11.0
                });
                // Independent pseudorandom draw per cell.
                let vals: Vec<f32> = (0..w * h).map(|_| rand()).collect();
                run(w, h, radius, |x, y| vals[y * w + x]);
            }
        }
    }

    /// A block-aligned single spike is the adversarial case for vHGW: it must
    /// be visible from exactly `2r+1` positions and no more.
    #[test]
    fn a_single_spike_spreads_to_exactly_the_window() {
        let (w, h, r) = (64usize, 1usize, 5usize);
        for spike in [0usize, 1, 10, 11, 12, 32, 62, 63] {
            let geom = PlaneGeometry {
                width: w,
                height: h,
            };
            let mut src = vec![0.0f32; w];
            src[spike] = 1.0;
            let mut scratch = vec![0.0f32; w];
            let mut got = vec![0.0f32; w];
            box_max(&src, geom, r, &mut scratch, &mut got);
            let lo = spike.saturating_sub(r);
            let hi = (spike + r).min(w - 1);
            let hits: Vec<usize> = (0..w).filter(|i| got[*i] == 1.0).collect();
            assert_eq!(hits, (lo..=hi).collect::<Vec<_>>(), "spike at {spike}");
        }
    }

    #[test]
    fn window_wider_than_the_plane_degenerates_to_the_global_max() {
        let geom = PlaneGeometry {
            width: 3,
            height: 3,
        };
        let src: Vec<f32> = (0..9).map(|i| i as f32).collect();
        let mut scratch = vec![0.0f32; 9];
        let mut got = vec![0.0f32; 9];
        box_max(&src, geom, 5, &mut scratch, &mut got);
        assert!(got.iter().all(|v| *v == 8.0), "{got:?}");
    }

    #[test]
    fn a_constant_plane_stays_constant_including_at_the_border() {
        // `-inf` padding leaking into the output would show up here.
        let geom = PlaneGeometry {
            width: 11,
            height: 7,
        };
        let src = vec![1234.5f32; geom.pixels()];
        let mut scratch = vec![0.0f32; geom.pixels()];
        let mut got = vec![0.0f32; geom.pixels()];
        box_max(&src, geom, 3, &mut scratch, &mut got);
        assert!(got.iter().all(|v| *v == 1234.5), "{got:?}");
    }

    #[test]
    fn radius_zero_is_the_identity() {
        let geom = PlaneGeometry {
            width: 4,
            height: 3,
        };
        let src: Vec<f32> = (0..12).map(|i| i as f32 * 2.0).collect();
        let mut scratch = vec![0.0f32; geom.pixels()];
        let mut got = vec![0.0f32; geom.pixels()];
        box_max(&src, geom, 0, &mut scratch, &mut got);
        assert_eq!(got, src);
    }

    /// `q = 1.0` must be the max exactly, which ties the two implementations
    /// together and makes the percentile arm's border policy checkable.
    #[test]
    fn the_top_quantile_is_the_running_max() {
        let (w, h) = (23usize, 19usize);
        let geom = PlaneGeometry {
            width: w,
            height: h,
        };
        let src: Vec<f32> = (0..w * h).map(|i| ((i * 37) % 101) as f32).collect();
        for radius in [1usize, 3, 7] {
            let mut scratch = vec![0.0f32; w * h];
            let mut m = vec![0.0f32; w * h];
            box_max(&src, geom, radius, &mut scratch, &mut m);
            let mut p = vec![0.0f32; w * h];
            window_percentile(&src, geom, radius, 1.0, &mut p);
            assert_eq!(m, p, "radius {radius}");
        }
    }

    /// The percentile's rank convention, checked against a hand-sorted window.
    #[test]
    fn the_percentile_rank_convention_is_floor_q_times_n() {
        let (w, h) = (5usize, 5usize);
        let geom = PlaneGeometry {
            width: w,
            height: h,
        };
        let src: Vec<f32> = (0..25).map(|i| i as f32).collect();
        let mut p = vec![0.0f32; 25];
        window_percentile(&src, geom, 2, 0.95, &mut p);
        // At the centre the window is the whole 5x5 plane: n = 25,
        // floor(0.95*25) = 23, so the 24th smallest of 0..24 is 23.
        assert_eq!(p[12], 23.0);
        window_percentile(&src, geom, 2, 0.5, &mut p);
        assert_eq!(p[12], 12.0);
    }
}
