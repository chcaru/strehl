//! Portable `ln` and `exp` for the pyramid fold's selection weight.
//!
//! # Why not `f32::ln` / `f32::exp`
//!
//! Those call the platform C runtime, whose results are neither correctly
//! rounded nor specified. MEASURED exhaustively on Windows (2026-11-08): its
//! `logf` differs from the correctly rounded value on 210,365 of the
//! 2,130,706,432 positive normal f32 inputs, and `expf` on 23,093 of the
//! 2,235,564,034 inputs in [-80, 80]. So the CPU merge was bit-reproducible
//! only for one C runtime, and no GPU could reproduce it.
//!
//! These evaluate in f64 using only addition, subtraction, multiplication,
//! division, `floor`, comparisons and f32 bit manipulation -- the operations
//! a GPU reproduces bit for bit when contraction is forbidden and f32 division
//! goes through f64 (MEASURED on an RTX 5090: 0 mismatches in 67 M samples).
//! Every constant is an exact f64 literal written out once here; a shader that
//! evaluates the same expressions in the same order with the same constants
//! returns the same bits.
//!
//! # Accuracy
//!
//! The f64 evaluation is accurate to a few units in 1e-16 relative, far below
//! f32 rounding, so the f32 result is the correctly rounded value except where
//! the exact result lies within that distance of an f32 rounding boundary.
//! `exhaustive_*` tests count those cases against an f64 reference.
//!
//! Choosing these over the C runtime changed the merge's output once, by at most
//! one f32 ulp in rare selection weights (see `STREHL_WEIGHT_MATH`).

/// `ln(2)`, f64 nearest.
const LN2: f64 = std::f64::consts::LN_2;
/// `1 / ln(2)`, f64 nearest.
const INV_LN2: f64 = std::f64::consts::LOG2_E;
/// `sqrt(2)`, f64 nearest.
const SQRT2: f64 = std::f64::consts::SQRT_2;

/// `1 / (2k + 1)` for `k = 0..=11`, the odd-power series of `atanh`.
pub const LN_SERIES: [f64; 12] = [
    1.0,
    1.0 / 3.0,
    1.0 / 5.0,
    1.0 / 7.0,
    1.0 / 9.0,
    1.0 / 11.0,
    1.0 / 13.0,
    1.0 / 15.0,
    1.0 / 17.0,
    1.0 / 19.0,
    1.0 / 21.0,
    1.0 / 23.0,
];

/// `1 / n!` for `n = 0..=14`.
pub const EXP_SERIES: [f64; 15] = [
    1.0,
    1.0,
    1.0 / 2.0,
    1.0 / 6.0,
    1.0 / 24.0,
    1.0 / 120.0,
    1.0 / 720.0,
    1.0 / 5040.0,
    1.0 / 40320.0,
    1.0 / 362880.0,
    1.0 / 3628800.0,
    1.0 / 39916800.0,
    1.0 / 479001600.0,
    1.0 / 6227020800.0,
    1.0 / 87178291200.0,
];

/// `2^k` as f64 for `-126 <= k <= 127`, built from f32 bits exactly as a
/// shader without f64 bit casts must build it.
#[inline]
fn pow2(k: i32) -> f64 {
    debug_assert!((-126..=127).contains(&k));
    f64::from(f32::from_bits(((k + 127) as u32) << 23))
}

/// Natural logarithm of an f32, evaluated in f64 and rounded once.
///
/// `ln(0) = -inf`, `ln(inf) = inf`, negative and NaN give NaN.
#[inline]
pub fn ln(x: f32) -> f32 {
    if x.is_nan() || x < 0.0 {
        return f32::NAN;
    }
    if x == 0.0 {
        return f32::NEG_INFINITY;
    }
    if x == f32::INFINITY {
        return f32::INFINITY;
    }
    let mut bits = x.to_bits();
    let mut e = ((bits >> 23) & 0xff) as i32;
    if e == 0 {
        // Subnormal: scale by 2^24 exactly, then remove it from the exponent.
        bits = (x * 16_777_216.0).to_bits();
        e = ((bits >> 23) & 0xff) as i32 - 24;
    }
    // Mantissa in [1, 2), exact in f64.
    let mut m = f64::from(f32::from_bits((bits & 0x007f_ffff) | 0x3f80_0000));
    let mut e = e - 127;
    if m > SQRT2 {
        m *= 0.5;
        e += 1;
    }
    // ln(m) = 2 atanh(s), s = (m - 1) / (m + 1), |s| <= 0.1716.
    let s = (m - 1.0) / (m + 1.0);
    let s2 = s * s;
    let mut p = LN_SERIES[11];
    let mut k = 11;
    while k > 0 {
        k -= 1;
        p = p * s2 + LN_SERIES[k];
    }
    let lnm = 2.0 * s * p;
    (f64::from(e) * LN2 + lnm) as f32
}

/// `e^x` of an f32, evaluated in f64 and rounded once.
///
/// Overflows to `inf` above ~88.72, underflows to `0` (through f32
/// subnormals) below ~-103.97; NaN gives NaN.
#[inline]
pub fn exp(x: f32) -> f32 {
    if x.is_nan() {
        return f32::NAN;
    }
    if x > 89.0 {
        return f32::INFINITY;
    }
    if x < -104.0 {
        return 0.0;
    }
    let xd = f64::from(x);
    let k = (xd * INV_LN2 + 0.5).floor();
    let r = xd - k * LN2;
    let mut p = EXP_SERIES[14];
    let mut n = 14;
    while n > 0 {
        n -= 1;
        p = p * r + EXP_SERIES[n];
    }
    // 2^k in two exact halves, each inside the f32 normal exponent range.
    let k = k as i32;
    let k1 = k / 2;
    (p * pow2(k1) * pow2(k - k1)) as f32
}

// ---------------------------------------------------------------------------
// f64 functions for the gate-floor probe's Box-Muller noise.
// ---------------------------------------------------------------------------

/// `1 / (2k + 1)` for `k = 0..=14`, the f64 `atanh` series.
pub const LN64_SERIES: [f64; 15] = [
    1.0,
    1.0 / 3.0,
    1.0 / 5.0,
    1.0 / 7.0,
    1.0 / 9.0,
    1.0 / 11.0,
    1.0 / 13.0,
    1.0 / 15.0,
    1.0 / 17.0,
    1.0 / 19.0,
    1.0 / 21.0,
    1.0 / 23.0,
    1.0 / 25.0,
    1.0 / 27.0,
    1.0 / 29.0,
];

/// `(-1)^k / (2k + 1)!` for `k = 0..=10`: sine's Taylor series.
pub const SIN_SERIES: [f64; 11] = [
    1.0,
    -1.0 / 6.0,
    1.0 / 120.0,
    -1.0 / 5040.0,
    1.0 / 362880.0,
    -1.0 / 39916800.0,
    1.0 / 6227020800.0,
    -1.0 / 1307674368000.0,
    1.0 / 355687428096000.0,
    -1.0 / 121645100408832000.0,
    1.0 / 51090942171709440000.0,
];

/// `(-1)^k / (2k)!` for `k = 0..=10`: cosine's Taylor series.
pub const COS_SERIES: [f64; 11] = [
    1.0,
    -1.0 / 2.0,
    1.0 / 24.0,
    -1.0 / 720.0,
    1.0 / 40320.0,
    -1.0 / 3628800.0,
    1.0 / 479001600.0,
    -1.0 / 87178291200.0,
    1.0 / 20922789888000.0,
    -1.0 / 6402373705728000.0,
    1.0 / 2432902008176640000.0,
];

/// `pi / 2` split for Cody-Waite reduction: the high part has 33 significant
/// bits, so `q * PIO2_HI` is exact for every quadrant `q` used here.
pub const PIO2_HI: f64 = 1.570_796_326_734_125_614_166_259_765_625;
pub const PIO2_LO: f64 = 6.077_100_506_506_192e-11;

/// `ln(k / 2^24)` for `1 <= k < 2^24`: the probe's uniform draw, which is a
/// 24-bit fixed-point fraction. `k` is exact in f32, so its exponent comes from
/// f32 bits, as a shader without f64 bit casts must take it.
#[inline]
pub fn ln_u24(k: u32) -> f64 {
    debug_assert!((1..1 << 24).contains(&k));
    let bits = (k as f32).to_bits();
    let mut e = ((bits >> 23) & 0xff) as i32 - 127;
    let mut m = f64::from(f32::from_bits((bits & 0x007f_ffff) | 0x3f80_0000));
    if m > SQRT2 {
        m *= 0.5;
        e += 1;
    }
    let s = (m - 1.0) / (m + 1.0);
    let s2 = s * s;
    let mut p = LN64_SERIES[14];
    let mut i = 14;
    while i > 0 {
        i -= 1;
        p = p * s2 + LN64_SERIES[i];
    }
    f64::from(e - 24) * LN2 + 2.0 * s * p
}

/// `(sin(th), cos(th))` for `0 <= th < 2 pi`.
#[inline]
pub fn sin_cos(th: f64) -> (f64, f64) {
    let q = (th / (PIO2_HI + PIO2_LO) + 0.5).floor();
    let r = th - q * PIO2_HI - q * PIO2_LO;
    let r2 = r * r;
    let mut s = SIN_SERIES[10];
    let mut c = COS_SERIES[10];
    let mut i = 10;
    while i > 0 {
        i -= 1;
        s = s * r2 + SIN_SERIES[i];
        c = c * r2 + COS_SERIES[i];
    }
    let (s, c) = (r * s, c);
    match (q as i64).rem_euclid(4) {
        0 => (s, c),
        1 => (c, -s),
        2 => (-s, -c),
        _ => (-c, s),
    }
}
/// `ln(1e-12)`: the probe's floor for a zero uniform draw.
pub const LN_UNIFORM_FLOOR: f64 = -27.631_021_115_928_547;

/// The gate-floor probe's Box-Muller pair from two 24-bit uniform draws
/// `k1, k2` (each the fraction `k / 2^24`): `(r cos th, r sin th)` with
/// `r = sqrt(-2 ln max(u1, 1e-12))` and `th = 2 pi u2`. Shared by the CPU fill
/// and the device's, so both make the same noise on any platform.
#[inline]
pub fn probe_gaussian_pair(k1: u32, k2: u32) -> (f64, f64) {
    let ln_u1 = if k1 == 0 {
        LN_UNIFORM_FLOOR
    } else {
        ln_u24(k1)
    };
    let r = (-2.0 * ln_u1).sqrt();
    let th = std::f64::consts::TAU * (f64::from(k2) / f64::from(1u32 << 24));
    let (s, c) = sin_cos(th);
    (r * c, r * s)
}
// ---------------------------------------------------------------------------
// An f32 screen for the probe pair, for devices whose f64 is slow.
//
// `probe_gaussian_pair_f32` uses only f32 add and multiply (and bit casts), so
// it is bit-reproducible on any IEEE-754 device that does not fuse them. Its
// distance from `probe_gaussian_pair` is bounded by exhaustive census over
// every 24-bit draw (`PROBE_F32_R_ERR`, `PROBE_F32_TRIG_ERR`); a quantised
// sample whose f32 value lies farther than `probe_f32_margin` from a rounding
// boundary is therefore exactly the f64 one, and only the rest need f64.
// ---------------------------------------------------------------------------

/// `1 / d` for `d` in `[1, 4)`: a bit-pattern seed and three Newton steps.
#[inline]
fn recip_f32(d: f32) -> f32 {
    let mut y = f32::from_bits(0x7EF3_11C3u32.wrapping_sub(d.to_bits()));
    for _ in 0..3 {
        y = y * (2.0 - d * y);
    }
    y
}

/// `sqrt(x)` for `x > 0` as `x * rsqrt(x)`: a bit-pattern seed and three
/// Newton steps.
#[inline]
fn sqrt_f32(x: f32) -> f32 {
    let mut y = f32::from_bits(0x5F37_59DFu32.wrapping_sub(x.to_bits() >> 1));
    for _ in 0..3 {
        y = y * (1.5 - 0.5 * x * y * y);
    }
    x * y
}

/// `ln(k / 2^24)` for `1 <= k < 2^24`, f32, the reduction of [`ln_u24`].
#[inline]
fn ln_u24_f32(k: u32) -> f32 {
    let bits = (k as f32).to_bits();
    let mut e = ((bits >> 23) & 0xff) as i32 - 127;
    let mut m = f32::from_bits((bits & 0x007f_ffff) | 0x3f80_0000);
    if m > std::f32::consts::SQRT_2 {
        m *= 0.5;
        e += 1;
    }
    let s = (m - 1.0) * recip_f32(m + 1.0);
    let s2 = s * s;
    let p = 1.0
        + s2 * (1.0 / 3.0 + s2 * (0.2 + s2 * (1.0 / 7.0 + s2 * (1.0 / 9.0 + s2 * (1.0 / 11.0)))));
    (e - 24) as f32 * std::f32::consts::LN_2 + 2.0 * s * p
}

/// `r = sqrt(-2 ln max(k1 / 2^24, 1e-12))` in f32.
#[inline]
pub fn probe_radius_f32(k1: u32) -> f32 {
    let ln_u1 = if k1 == 0 {
        LN_UNIFORM_FLOOR as f32
    } else {
        ln_u24_f32(k1)
    };
    sqrt_f32(-2.0 * ln_u1)
}

/// `(cos th, sin th)` for `th = 2 pi k2 / 2^24` in f32: the quadrant from the
/// draw's top bits (exact), the remainder in `[-pi/4, pi/4)` by Taylor series.
#[inline]
pub fn probe_trig_f32(k2: u32) -> (f32, f32) {
    let q = (k2 + (1 << 21)) >> 22;
    let f = k2 as i32 - (q << 22) as i32;
    let x = f as f32 * (std::f32::consts::FRAC_PI_2 / (1u32 << 22) as f32);
    let x2 = x * x;
    let s = x
        * (1.0
            + x2 * (-1.0 / 6.0
                + x2 * (1.0 / 120.0 + x2 * (-1.0 / 5040.0 + x2 * (1.0 / 362_880.0)))));
    let c = 1.0
        + x2 * (-0.5
            + x2 * (1.0 / 24.0
                + x2 * (-1.0 / 720.0 + x2 * (1.0 / 40320.0 + x2 * (-1.0 / 3_628_800.0)))));
    match q & 3 {
        0 => (c, s),
        1 => (-s, c),
        2 => (-c, -s),
        _ => (s, -c),
    }
}

/// [`probe_gaussian_pair`] screened in f32: `(r cos th, r sin th)`.
#[inline]
pub fn probe_gaussian_pair_f32(k1: u32, k2: u32) -> (f32, f32) {
    let r = probe_radius_f32(k1);
    let (c, s) = probe_trig_f32(k2);
    (r * c, r * s)
}

/// Census bound on `|probe_radius_f32(k1) - r(k1)|` over every `k1`:
/// MEASURED 8.41e-7 (`tests::probe_f32_census`), rounded up.
pub const PROBE_F32_R_ERR: f64 = 1.0e-6;
/// Census bound on the f32 cosine and sine's error over every `k2`:
/// MEASURED 9.75e-8, rounded up.
pub const PROBE_F32_TRIG_ERR: f64 = 1.2e-7;
/// The largest radius: `k1 = 0`, `sqrt(-2 ln 1e-12)`.
pub const PROBE_MAX_RADIUS: f64 = 7.433_844_377_699_676_5;

/// A bound on `|level + sigma g_f32 - (level + sigma g)|` (the right side in
/// f64, `g_f32` widened exactly) for either value of a pair, doubled for
/// margin. A screened value farther than this from every half-integer
/// quantises exactly as the f64 one does.
pub fn probe_f32_margin(sigma: f64) -> f64 {
    let (er, et, r) = (PROBE_F32_R_ERR, PROBE_F32_TRIG_ERR, PROBE_MAX_RADIUS);
    let g = er * (1.0 + et) + r * et + (r + er) * (1.0 + et) * f64::from(f32::EPSILON) * 0.5;
    2.0 * sigma.abs() * g + 1e-9
}
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn special_values() {
        assert!(ln(f32::NAN).is_nan() && ln(-1.0).is_nan());
        assert_eq!(ln(0.0), f32::NEG_INFINITY);
        assert_eq!(ln(f32::INFINITY), f32::INFINITY);
        assert_eq!(ln(1.0).to_bits(), 0.0f32.to_bits());
        assert!(exp(f32::NAN).is_nan());
        assert_eq!(exp(0.0), 1.0);
        assert_eq!(exp(100.0), f32::INFINITY);
        assert_eq!(exp(-200.0), 0.0);
        assert_eq!(exp(f32::NEG_INFINITY), 0.0);
        assert_eq!(exp(f32::INFINITY), f32::INFINITY);
        // Subnormal ln is finite and continuous with the normal range.
        let tiny = f32::from_bits(1);
        assert!((ln(tiny) - (f64::from(tiny).ln() as f32)).abs() <= 1e-5);
    }

    /// Every f32 in a range against the f64 function rounded to f32. Not
    /// bit-equality: the reference itself can be off by one at a boundary.
    fn census(lo: u32, hi: u32, step: u32, f: impl Fn(f32) -> (f32, f32)) -> (u64, u64, u32) {
        let (mut n, mut bad, mut worst) = (0u64, 0u64, 0u32);
        let mut u = lo;
        while u <= hi {
            let (got, want) = f(f32::from_bits(u));
            n += 1;
            if got.to_bits() != want.to_bits() {
                bad += 1;
                worst = worst.max(got.to_bits().abs_diff(want.to_bits()));
            }
            match u.checked_add(step) {
                Some(v) => u = v,
                None => break,
            }
        }
        (n, bad, worst)
    }

    #[test]
    fn ln_is_correctly_rounded_on_a_dense_sample() {
        let (n, bad, worst) = census(1, 0x7f7f_ffff, 97, |x| (ln(x), f64::from(x).ln() as f32));
        assert!(worst <= 1, "{bad} of {n} differ, worst {worst} ulp");
        assert!((bad as f64) < 1e-6 * n as f64, "{bad} of {n} differ");
    }

    #[test]
    fn exp_is_correctly_rounded_on_a_dense_sample() {
        let lo = (-104.0f32).to_bits();
        let (n1, b1, w1) = census(0x8000_0001, lo, 53, |x| (exp(x), f64::from(x).exp() as f32));
        let (n2, b2, w2) = census(0, 89.0f32.to_bits(), 53, |x| {
            (exp(x), f64::from(x).exp() as f32)
        });
        assert!(w1 <= 1 && w2 <= 1, "worst {w1} / {w2} ulp");
        assert!(
            ((b1 + b2) as f64) < 1e-6 * (n1 + n2) as f64,
            "{} of {} differ",
            b1 + b2,
            n1 + n2
        );
    }

    #[test]
    fn the_probe_functions_track_the_platform_to_a_few_ulp() {
        let ulps = |a: f64, b: f64| (a.to_bits() as i64 - b.to_bits() as i64).unsigned_abs();
        let mut worst_ln = 0;
        for k in (1u32..1 << 24).step_by(7) {
            let want = (f64::from(k) / f64::from(1u32 << 24)).ln();
            worst_ln = worst_ln.max(ulps(ln_u24(k), want));
        }
        let (mut worst_s, mut worst_c) = (0u64, 0u64);
        for k in (0u32..1 << 24).step_by(5) {
            let th = std::f64::consts::TAU * (f64::from(k) / f64::from(1u32 << 24));
            let (s, c) = sin_cos(th);
            // Compare absolute error in units of the result's scale, since
            // near a zero crossing ulps of a tiny value are meaningless.
            let es = ((s - th.sin()).abs() / f64::EPSILON).ceil() as u64;
            let ec = ((c - th.cos()).abs() / f64::EPSILON).ceil() as u64;
            worst_s = worst_s.max(es);
            worst_c = worst_c.max(ec);
        }
        eprintln!("ln worst {worst_ln} ulp; sin/cos worst {worst_s}/{worst_c} eps");
        assert!(worst_ln <= 4, "ln {worst_ln} ulp");
        assert!(
            worst_s <= 8 && worst_c <= 8,
            "sin {worst_s} cos {worst_c} eps"
        );
    }
    #[test]
    #[ignore = "census over every probe draw; prints mismatch counts"]
    fn probe_function_census() {
        let (mut ln_miss, mut s_miss, mut c_miss) = (0u32, 0u32, 0u32);
        for k in 1u32..1 << 24 {
            let u = f64::from(k) / f64::from(1u32 << 24);
            ln_miss += u32::from(ln_u24(k) != u.ln());
            let th = std::f64::consts::TAU * u;
            let (s, c) = sin_cos(th);
            s_miss += u32::from(s != th.sin());
            c_miss += u32::from(c != th.cos());
        }
        let th0 = sin_cos(0.0);
        eprintln!(
            "ln {ln_miss}, sin {s_miss}, cos {c_miss} of 2^24; ln(1e-12) = {:?}; sin_cos(0) = {th0:?}",
            1e-12f64.ln()
        );
    }
    #[test]
    #[ignore = "quantised probe noise, platform against portable functions"]
    fn probe_noise_census() {
        let mut flips = 0u64;
        let mut total = 0u64;
        for (case, (level, sigma)) in [(64.0, 3.0), (512.0, 9.5), (2048.0, 30.0), (9000.0, 120.0)]
            .into_iter()
            .enumerate()
        {
            let mut s: u64 = 0x2545_F491_4F6C_DD1D ^ case as u64;
            let mut next = || {
                s = s.wrapping_add(0x9E37_79B9_7F4A_7C15);
                let mut z = s;
                z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
                z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
                ((z ^ (z >> 31)) >> 40) as u32
            };
            let q = |g: f64| (level + sigma * g).round().clamp(0.0, 65535.0) as u16;
            for _ in 0..(1u64 << 27) {
                let (k1, k2) = (next(), next());
                let u1 = (f64::from(k1) / f64::from(1u32 << 24)).max(1e-12);
                let u2 = f64::from(k2) / f64::from(1u32 << 24);
                let r = (-2.0 * u1.ln()).sqrt();
                let th = std::f64::consts::TAU * u2;
                let lnp = if k1 == 0 {
                    -27.631_021_115_928_547
                } else {
                    ln_u24(k1)
                };
                let rp = (-2.0 * lnp).sqrt();
                let (sp, cp) = sin_cos(th);
                flips += u64::from(q(r * th.sin()) != q(rp * sp));
                flips += u64::from(q(r * th.cos()) != q(rp * cp));
                total += 2;
            }
        }
        eprintln!("probe noise: {flips} of {total} quantised samples differ");
    }
    #[test]
    fn probe_f32_census() {
        // Every 24-bit draw: the f32 screen's error against the f64 pair's
        // factors, which the margin's constants must bound.
        let mut er = 0.0f64;
        for k1 in 0u32..1 << 24 {
            let ln_u1 = if k1 == 0 {
                LN_UNIFORM_FLOOR
            } else {
                ln_u24(k1)
            };
            let r = (-2.0 * ln_u1).sqrt();
            er = er.max((f64::from(probe_radius_f32(k1)) - r).abs());
        }
        let mut et = 0.0f64;
        for k2 in 0u32..1 << 24 {
            let th = std::f64::consts::TAU * (f64::from(k2) / f64::from(1u32 << 24));
            let (s, c) = sin_cos(th);
            let (c32, s32) = probe_trig_f32(k2);
            et = et
                .max((f64::from(c32) - c).abs())
                .max((f64::from(s32) - s).abs());
        }
        eprintln!("probe f32 census: radius {er:e}, trig {et:e}");
        assert!(
            er <= PROBE_F32_R_ERR,
            "radius error {er:e} exceeds the bound"
        );
        assert!(
            et <= PROBE_F32_TRIG_ERR,
            "trig error {et:e} exceeds the bound"
        );
        assert_eq!(PROBE_MAX_RADIUS, (-2.0 * LN_UNIFORM_FLOOR).sqrt());
    }
}
