"""Is the tangential arm blur-matched to the radial arm?

ORCH proposes a tangentially-rotated correction as the placebo for the
resampler, on the argument: "same code path, same interpolation kernel, same
number of resampled sensels, same blur". The first three hold. The fourth is
the one that matters and it is not free -- interpolation blur depends on the
SUB-PIXEL PHASE of the displacement along each pixel axis, not on its
magnitude. Radial and tangential have equal magnitude by construction but
distribute that magnitude differently between the x and y axes at any given
azimuth.

Two claims, both measured here rather than argued:

  A. Bilinear attenuation is EXACTLY symmetric under a sign flip of the shift.
     If true, an ANTI-RADIAL arm (-d instead of +d) is blur-matched to the
     radial arm pixel-for-pixel, at the same location, on the same content --
     strictly better matched than tangential, and a negative DOSE rather than
     a null.

  B. Radial and tangential blur differ at a fixed azimuth, and the difference
     is largest on ORIENTED content -- which is what ORCH's crops contain
     (hairs at r=0.50, wing membrane texture at r=0.83).

M111 contributes the interpolation arithmetic only. optics.rs is M107's lane
and is not read or touched here; this reasons about bilinear resampling in
general, not about strehl's implementation.
"""
import numpy as np

RNG = np.random.default_rng(20260824)
BAND = 0.35  # high-frequency band, in cycles/sample, over which to score


def bilinear_shift(img, dx, dy):
    """Shift by (dx, dy) with bilinear interpolation, wrapping at the edges.

    Wrapping keeps the comparison free of boundary effects, which would
    otherwise differ between an x-shift and a y-shift and confound claim B.
    """
    ix, iy = int(np.floor(dx)), int(np.floor(dy))
    fx, fy = dx - ix, dy - iy
    out = np.zeros_like(img, dtype=float)
    for (ox, oy, w) in ((0, 0, (1 - fx) * (1 - fy)),
                        (1, 0, fx * (1 - fy)),
                        (0, 1, (1 - fx) * fy),
                        (1, 1, fx * fy)):
        out += w * np.roll(np.roll(img, -(ix + ox), axis=1), -(iy + oy), axis=0)
    return out


def hf_retention(before, after):
    """Fraction of high-frequency energy surviving the shift."""
    fy = np.fft.fftfreq(before.shape[0])[:, None]
    fx = np.fft.fftfreq(before.shape[1])[None, :]
    mask = np.hypot(fx, fy) >= BAND
    e0 = float(np.abs(np.fft.fft2(before))[mask].__pow__(2).sum())
    e1 = float(np.abs(np.fft.fft2(after))[mask].__pow__(2).sum())
    return e1 / e0


iso = RNG.standard_normal((256, 256))

print("=" * 72)
print("INSTRUMENT CHECK -- bilinear blur must peak at f=0.5 and vanish at f=0,1")
print("=" * 72)
r0 = hf_retention(iso, bilinear_shift(iso, 0.0, 0.0))
r5 = hf_retention(iso, bilinear_shift(iso, 0.5, 0.0))
r1 = hf_retention(iso, bilinear_shift(iso, 1.0, 0.0))
print(f"   shift 0.0 -> retention {r0:.6f}   (expect 1, integer shift cannot blur)")
print(f"   shift 0.5 -> retention {r5:.6f}   (expect minimum)")
print(f"   shift 1.0 -> retention {r1:.6f}   (expect 1, integer shift cannot blur)")
assert abs(r0 - 1.0) < 1e-9 and abs(r1 - 1.0) < 1e-9, "instrument dead: integer shift blurred"
assert r5 < r0, "instrument dead: half-pixel shift did not blur"
print("   instrument live\n")

print("=" * 72)
print("CLAIM A -- is bilinear blur symmetric under a SIGN FLIP of the shift?")
print("   (if yes, an ANTI-RADIAL arm is exactly blur-matched to the radial arm)")
print("=" * 72)
worst = 0.0
for d in (0.069, 0.108, 0.147, 0.155, 0.189, 0.224, 0.3, 0.45):
    a = hf_retention(iso, bilinear_shift(iso, +d, 0.0))
    b = hf_retention(iso, bilinear_shift(iso, -d, 0.0))
    worst = max(worst, abs(a - b))
    print(f"   |d|={d:.3f}   +d {a:.9f}   -d {b:.9f}   diff {abs(a - b):.2e}")
print(f"\n   worst |retention(+d) - retention(-d)| = {worst:.2e}")
assert worst < 1e-12, "claim A refuted: sign flip changes the blur"
print("   CLAIM A HOLDS: the sign flip is blur-neutral to machine precision.")
print("   => an anti-radial arm matches the radial arm's blur EXACTLY, at the")
print("      same location, on the same content, and doubles CA instead of")
print("      removing it -- a negative dose, not a null.\n")

print("=" * 72)
print("CLAIM B -- do radial and tangential blur differ at a FIXED azimuth?")
print("=" * 72)
# At azimuth theta the radial shift is d*(cos,sin) and the tangential is
# d*(-sin,cos): equal magnitude, but the axis split differs. Worst case is
# theta = 0, where radial is purely x and tangential purely y.
d = 0.155
print(f"   displacement magnitude {d} px, azimuth 0 deg")
print(f"   radial     -> (dx,dy) = ({d:+.3f}, {0:+.3f})")
print(f"   tangential -> (dx,dy) = ({0:+.3f}, {d:+.3f})\n")

# Oriented content, as in ORCH's crops: smooth ALONG the hair, sharp ACROSS it.
hairs = RNG.standard_normal((256, 256))
k = np.exp(-0.5 * (np.arange(-15, 16) / 4.0) ** 2)
k /= k.sum()
hairs = np.apply_along_axis(lambda m: np.convolve(m, k, mode="same"), 0, hairs)

for name, img in (("isotropic noise", iso), ("ORIENTED (hair-like)", hairs)):
    rad = hf_retention(img, bilinear_shift(img, +d, 0.0))
    tan = hf_retention(img, bilinear_shift(img, 0.0, +d))
    rel = abs(rad - tan) / rad * 100.0
    print(f"   {name:22s} radial {rad:.6f}   tangential {tan:.6f}   "
          f"differ by {rel:5.2f}%")

rad_h = hf_retention(hairs, bilinear_shift(hairs, +d, 0.0))
tan_h = hf_retention(hairs, bilinear_shift(hairs, 0.0, +d))
assert abs(rad_h - tan_h) / rad_h > 0.01, "claim B refuted: oriented content agreed"
print("\n   CLAIM B HOLDS on oriented content: at a fixed azimuth the two arms")
print("   blur along DIFFERENT axes, so they are matched only in ring-average,")
print("   not in a crop. ORCH's visual evidence is crops of hairs and membrane")
print("   texture, which are oriented.")
print("=" * 72)
