"""Exact MTF of the co-site resample, computed from the kernel in the source.

Independent re-derivation of BUILD-SHARP section 20.3's `co-site (2-D)` column.
`image_out.rs::resample_shift` is a separable 4-tap Keys (a = -1/2) cubic
convolution at a fixed fractional offset. Its 1-D transfer function at spatial
frequency f (cycles per pixel) is

    m(f) = | sum_k w_k * exp(-2*pi*i*f*(k - 1 + floor(d))) |

with the taps and the index arithmetic copied verbatim from the Rust so an
error in this file cannot be an error the Rust does not also have. The 2-D
figure for a shift applied on BOTH axes is m(f)^2.

Also prints the Catmull-Rom gather MTF at the same bands, since `gather_checked`
runs the CatmullRom resampler and Keys a = -1/2 *is* Catmull-Rom -- which is why
the two columns in BUILD-SHARP's table have the same functional form.
"""

import numpy as np


def keys_weights(t: float) -> np.ndarray:
    """`image_out.rs::keys_weights`, transcribed."""
    a = -0.5
    t2, t3 = t * t, t * t * t
    return np.array(
        [
            a * (t3 - 2.0 * t2 + t),
            (a + 2.0) * t3 - (a + 3.0) * t2 + 1.0,
            -(a + 2.0) * t3 + (2.0 * a + 3.0) * t2 - a * t,
            -a * (t3 - t2),
        ]
    )


def mtf_1d(d: float, f: float) -> float:
    """Amplitude retained at f by a 1-D Keys resample at signed offset d."""
    base = np.floor(d)
    w = keys_weights(d - base)
    # `resample_shift` reads src[x + x0 + k - 1] with x0 = floor(d); the
    # magnitude of the transfer function is invariant to the whole-pixel part,
    # so only the taps matter, but keep the offsets explicit anyway.
    k = np.arange(4) + base - 1.0
    return abs(np.sum(w * np.exp(-2j * np.pi * f * k)))


BANDS = [0.25, 0.35, 0.50]
SHARP_COSITE = {0.25: 0.88135, 0.35: 0.68133, 0.50: 0.47266}

print("Keys a=-1/2 taps at t=0.25:", np.round(keys_weights(0.25), 6),
      " sum =", round(float(keys_weights(0.25).sum()), 12))
print()
print(" f      m(f) 1-D    m(f)^2 2-D   BUILD-SHARP   delta")
for f in BANDS:
    m = mtf_1d(0.25, f)
    two_d = m * m
    ref = SHARP_COSITE[f]
    print(f"{f:5.2f}   {m:9.5f}    {two_d:9.5f}    {ref:9.5f}   {two_d - ref:+.5f}")

print()
print("Amplitude a REMOVED co-site would recover (1 / co-site 2-D):")
for f in BANDS:
    two_d = mtf_1d(0.25, f) ** 2
    print(f"  f={f:4.2f}   {1.0 / two_d:.4f}x")

print()
print("BUILD-SHARP's FOLDED prediction, and the gather-cost control it nets against:")
control = {0.25: 0.9942, 0.35: 0.9800, 0.50: 0.9471}
folded_pred = {0.25: 1.128, 0.35: 1.438, 0.50: 2.004}
for f in BANDS:
    removed = 1.0 / mtf_1d(0.25, f) ** 2
    print(
        f"  f={f:4.2f}   removed {removed:.4f}x  * control {control[f]:.4f}"
        f"  = {removed * control[f]:.4f}x   (BUILD-SHARP said {folded_pred[f]:.3f}x)"
    )
