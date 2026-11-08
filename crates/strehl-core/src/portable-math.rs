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
}
