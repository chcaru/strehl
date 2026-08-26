"""Where do the per-channel ceilings diverge? Read the master back into the
space the decision is made in.

BUILD-CHROMA 25.2 reports the master's per-channel maxima as R 42213, G 38921,
B 52239 and notes there is no plateau at any of them. Those are LINEAR sRGB
numbers, i.e. POST-matrix, and the matrix mixes channels -- so they cannot by
themselves locate a ceiling. This script inverts the matrix and looks at the
white-balanced camera triple the renderer actually held, which is the space
`color::Render::clip_highlights` makes its decision in.

Three things are reported, and each is a number the fix depends on:

  1. `ceil_c = K0 * wb_c` -- the level at which a CONTAINER-PINNED raw sample
     lands, per channel, in the render's normalised units. Green's is the
     smallest because green's white-balance gain is 1.0 by construction. This is
     the divergence, and it is arithmetic, not an estimate.

  2. `u_c = v_c / ceil_c` -- how much of its own headroom each channel has used.
     A pixel with `u_G` near 1 has a green sample that is at or near "at least
     this bright" rather than a measurement, while `u_B` near 0.6 means blue is
     still measuring. That gap IS the colour error.

  3. The post-matrix clamp census. The inversion in (2) is only valid where
     nothing clamped, so that is asserted rather than assumed.
"""

import sys

import numpy as np

sys.path.insert(0, __file__.rsplit("\\", 1)[0])
from common import (BLACK, CONTAINER, FOAM_WB, K0, WHITE, back_to_camera,
                    ceilings, dump, load_master, to_srgb)


def main():
    path = sys.argv[1]
    tag = sys.argv[2] if len(sys.argv) > 2 else "h2"
    a = load_master(path)
    f = a.astype(np.float32)

    print("=" * 92)
    print("0. THE ARITHMETIC OF THE CEILING (no image involved)")
    print("=" * 92)
    print(f"  black {BLACK:.0f}  Levels::white {WHITE:.0f}  CONTAINER_MAX_DN {CONTAINER:.0f}")
    print(f"  K0 = (container - black) / (white - black) = {K0:.6f}")
    ceil = ceilings(FOAM_WB)
    for c, n in enumerate("RGB"):
        print(f"    {n}: wb {FOAM_WB[c]:.6f}  ->  ceiling {ceil[c]:.6f}   "
              f"(= {ceil[c] / ceil[1]:.4f} x green's)")
    print(f"  K = min_c ceiling = {ceil.min():.6f}  (green, by construction: its gain is 1.0)")
    print(f"  BLUE HAS {ceil[2] / ceil[1]:.4f}x GREEN'S HEADROOM AND RED {ceil[0] / ceil[1]:.4f}x.")

    print()
    print("=" * 92)
    print("1. POST-MATRIX CLAMP CENSUS -- is the inversion below valid?")
    print("=" * 92)
    for c, n in enumerate("RGB"):
        v = f[..., c]
        print(f"  {n}: max {v.max():7.0f} ({v.max() / 65535 * 100:6.2f}% FS)   "
              f"at 65535: {(v >= 65535).mean() * 100:.6f}%   at 0: {(v <= 0).mean() * 100:.4f}%")
    clamped = (f >= 65535).any(axis=2)
    print(f"  pixels with ANY channel at full scale: {clamped.mean() * 100:.4f}%")
    print("  The inversion below is exact only where nothing clamped, so the clamped")
    print("  population is EXCLUDED from it and counted here instead. A clamped sample")
    print("  is a lower bound in the output as well as in the sensor.")
    valid = ~clamped
    assert valid.mean() > 0.9, "too little unclamped data for the inversion to mean anything"

    print()
    print("=" * 92)
    print("2. THE SAME IMAGE IN WHITE-BALANCED CAMERA SPACE (where the ceiling lives)")
    print("=" * 92)
    cam = back_to_camera(a)
    # Round-trip control: the inversion must reproduce the file where nothing
    # clamped. Run on the valid population only, for the reason stated above.
    m = to_srgb().astype(np.float32)
    back = np.clip(cam @ m.T, 0.0, 1.0) * 65535.0
    err = np.abs(back - f)[valid].max()
    print(f"  round-trip control (unclamped px): max |reconstructed - file| = {err:.2f} DN "
          f"of 65535 ({err / 65535 * 100:.5f}%)")
    assert err < 6.0, "the inversion does not reproduce the file; every number below is void"

    print(f"  {'chan':>4} {'ceiling':>9} {'max v':>9} {'max u':>8} {'p99.99 u':>9} "
          f"{'u>0.5':>9} {'u>0.8':>9} {'u>0.95':>9}")
    stats = {}
    for c, n in enumerate("RGB"):
        v = cam[..., c][valid]
        u = v / ceil[c]
        stats[n] = {"ceiling": float(ceil[c]), "max_v": float(v.max()),
                    "max_u": float(u.max())}
        print(f"  {n:>4} {ceil[c]:9.4f} {v.max():9.4f} {u.max():8.4f} "
              f"{np.percentile(u, 99.99):9.4f} "
              f"{(u > 0.5).mean() * 100:8.4f}% {(u > 0.8).mean() * 100:8.4f}% "
              f"{(u > 0.95).mean() * 100:8.4f}%")

    umax = np.max(cam / ceil[None, None, :], axis=2)[valid]
    print()
    print("  u_max = max_c (v_c / ceil_c) -- the driver a roll-off would key on:")
    for q in (99.0, 99.5, 99.9, 99.99, 100.0):
        print(f"    p{q:<6}: {np.percentile(umax, q):.4f}")
    for t in (0.5, 0.6, 0.7, 0.8, 0.9, 1.0):
        print(f"    u_max > {t:.2f}: {(umax > t).mean() * 100:8.4f}%  "
              f"({int((umax > t).sum()):,} px)")

    print()
    print("=" * 92)
    print("3. WHICH CHANNEL IS THE ARGMAX OF u, AMONG THE BRIGHTEST 0.76%?")
    print("=" * 92)
    lum = f.max(axis=2)
    hot = (lum >= np.percentile(lum, 100 - 0.76)) & valid
    u = cam / ceil[None, None, :]
    who = np.argmax(u, axis=2)
    print(f"  hot AND unclamped pixels: {int(hot.sum()):,}")
    for c, n in enumerate("RGB"):
        print(f"    {n} is the nearest-to-its-own-ceiling channel on "
              f"{(who[hot] == c).mean() * 100:6.2f}% of them "
              f"(whole frame {(who[valid] == c).mean() * 100:6.2f}%)")
    print(f"  mean u among hot pixels: "
          f"R {u[..., 0][hot].mean():.4f}  G {u[..., 1][hot].mean():.4f}  "
          f"B {u[..., 2][hot].mean():.4f}")
    print(f"  mean u over the unclamped frame: "
          f"R {u[..., 0][valid].mean():.4f}  G {u[..., 1][valid].mean():.4f}  "
          f"B {u[..., 2][valid].mean():.4f}")

    dump(tag, {"ceilings": {n: float(ceil[c]) for c, n in enumerate("RGB")},
               "K0": K0, "per_channel": stats,
               "umax_p9999": float(np.percentile(umax, 99.99)),
               "umax_max": float(umax.max())})


if __name__ == "__main__":
    main()
