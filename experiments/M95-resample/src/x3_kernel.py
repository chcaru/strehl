"""M95 arm 4 - is strehl's gather as good as a Catmull-Rom should be, and what would a
better kernel buy?

x2 measured that ONE gather costs 0.2851 dex on real data (B0 -> B1, a 0.9974 zoom).
That number alone does not say whether the loss is INTRINSIC to Catmull-Rom or whether
strehl's implementation is worse than the kernel it names.

This script writes Catmull-Rom from its own definition, applies it to B0's tiles at
known sub-pixel phases, and measures the cost with the SAME band_ratio instrument. If
the independent Catmull-Rom lands near 0.2851 dex, the loss is the kernel and the fix is
a better kernel. If it lands far below, strehl's gather has a defect.

Then it prices the alternatives on the same axis, so the report can say what a fix buys
rather than asserting that one would help.
"""

import json
import os

import numpy as np

from x2_pairs import IMAGES, TILE, band_ratio, load_luma, pick_tiles

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")
PAD = 16


def w_catmullrom(t):
    """Keys cubic with B=0, C=0.5. The sharp end of the BC-cubic family."""
    t = np.asarray(t, dtype=np.float64)
    a = np.abs(t)
    a2, a3 = a * a, a * a * a
    w = np.where(a <= 1.0, 1.5 * a3 - 2.5 * a2 + 1.0, 0.0)
    w = np.where((a > 1.0) & (a < 2.0), -0.5 * a3 + 2.5 * a2 - 4.0 * a + 2.0, w)
    return w


def w_mitchell(t):
    """B=C=1/3. Deliberately included as a NEGATIVE control: Mitchell is BLURRIER than
    Catmull-Rom by construction, so it must price WORSE. A kernel comparison that cannot
    rank a known-blurrier kernel below the incumbent is not measuring sharpness."""
    t = np.asarray(t, dtype=np.float64)
    a = np.abs(t)
    a2, a3 = a * a, a * a * a
    B = C = 1.0 / 3.0
    p = ((12 - 9 * B - 6 * C) * a3 + (-18 + 12 * B + 6 * C) * a2 + (6 - 2 * B)) / 6.0
    q = ((-B - 6 * C) * a3 + (6 * B + 30 * C) * a2 + (-12 * B - 48 * C) * a + (8 * B + 24 * C)) / 6.0
    return np.where(a < 1.0, p, np.where(a < 2.0, q, 0.0))


def w_lanczos3(t):
    t = np.asarray(t, dtype=np.float64)
    a = np.abs(t)
    with np.errstate(invalid="ignore", divide="ignore"):
        v = np.sinc(t) * np.sinc(t / 3.0)
    return np.where(a < 3.0, v, 0.0)


KERNELS = {
    "catmullrom": (w_catmullrom, 2),
    "mitchell": (w_mitchell, 2),
    "lanczos3": (w_lanczos3, 3),
}


def shift1d(a, axis, frac, wfun, radius):
    """Separable sub-pixel translation by `frac` along `axis`."""
    a = np.moveaxis(a, axis, 0)
    taps = np.arange(-radius + 1, radius + 1)
    w = wfun(frac - taps)
    w = w / w.sum()
    out = np.zeros_like(a, dtype=np.float64)
    for t, wt in zip(taps, w):
        out += wt * np.roll(a, -t, axis=0)
    return np.moveaxis(out, 0, axis)


def resample(tile, dy, dx, name):
    wfun, radius = KERNELS[name]
    t = shift1d(tile.astype(np.float64), 0, dy, wfun, radius)
    return shift1d(t, 1, dx, wfun, radius)


def bspline_prefilter(a, axis):
    """Exact cubic B-spline INTERPOLATION (Unser). The prefilter inverts the B-spline
    basis so the result passes through the samples; the effective kernel is far flatter
    to Nyquist than Keys. This is the standard high-quality fix."""
    z = np.sqrt(3.0) - 2.0
    a = np.moveaxis(a.astype(np.float64), axis, 0).copy()
    n = a.shape[0]
    k = np.arange(min(n, 32))
    c0 = (a[: len(k)] * (z ** k)[:, None]).sum(axis=0) / (1.0 - z ** (2 * n))
    a *= 6.0
    a[0] = c0 * 6.0
    for i in range(1, n):
        a[i] += z * a[i - 1]
    a[-1] = (z / (z * z - 1.0)) * (a[-1] + z * a[-2])
    for i in range(n - 2, -1, -1):
        a[i] = z * (a[i + 1] - a[i])
    return np.moveaxis(a, 0, axis)


def w_bspline(t):
    t = np.asarray(t, dtype=np.float64)
    a = np.abs(t)
    return np.where(
        a < 1.0,
        (4.0 - 6.0 * a * a + 3.0 * a**3) / 6.0,
        np.where(a < 2.0, ((2.0 - a) ** 3) / 6.0, 0.0),
    )


def resample_bspline(tile, dy, dx):
    c = bspline_prefilter(bspline_prefilter(tile, 0), 1)
    t = shift1d(c, 0, dy, w_bspline, 2)
    return shift1d(t, 1, dx, w_bspline, 2)


def main():
    b0 = load_luma(IMAGES["B0"]["path"])
    tiles = pick_tiles(b0)
    print(f"{len(tiles)} tiles, same selection as x2 (sharpest by gradient on B0)\n")

    base = np.array([band_ratio(b0[y : y + TILE, x : x + TILE], 1.0) for y, x in tiles])
    print(f"B0 baseline mean log10(hi/lo) = {base.mean():+.4f}\n")

    # phases: a zoom sweeps the sub-pixel phase uniformly across the field, so the
    # honest comparison to a real render is phase-AVERAGED, not the worst phase.
    phases = [(0.0, 0.0), (0.5, 0.0), (0.0, 0.5), (0.5, 0.5), (0.25, 0.25), (0.25, 0.75), (0.75, 0.25), (0.75, 0.75)]

    results = {}
    print(f"{'kernel':12s} {'phase-avg':>10s} {'worst phase':>12s} {'phase (0,0)':>12s}   (dex vs B0)")
    for name in ["catmullrom", "mitchell", "lanczos3", "bspline"]:
        per_phase = []
        for dy, dx in phases:
            vals = []
            for y, x in tiles:
                t = b0[y - PAD : y + TILE + PAD, x - PAD : x + TILE + PAD]
                r = resample_bspline(t, dy, dx) if name == "bspline" else resample(t, dy, dx, name)
                vals.append(band_ratio(r[PAD:-PAD, PAD:-PAD], 1.0))
            per_phase.append(float(np.mean(vals) - base.mean()))
        nonzero = [p for p, ph in zip(per_phase, phases) if ph != (0.0, 0.0)]
        results[name] = dict(
            phase_avg=float(np.mean(nonzero)),
            worst=float(np.min(per_phase)),
            identity=per_phase[0],
            per_phase=per_phase,
        )
        print(
            f"{name:12s} {np.mean(nonzero):+10.4f} {np.min(per_phase):+12.4f} {per_phase[0]:+12.4f}"
        )

    print("\n--- identity-phase control ---")
    print("  A shift of (0,0) must cost ~0 for every INTERPOLATING kernel (they all pass")
    print("  through the samples). A non-zero value there is an implementation bug.")
    for name, r in results.items():
        flag = "ok" if abs(r["identity"]) < 0.01 else "*** NON-ZERO AT IDENTITY ***"
        print(f"  {name:12s} {r['identity']:+.6f}  {flag}")

    print("\n--- ordering control (Mitchell must be worse than Catmull-Rom) ---")
    ok = results["mitchell"]["phase_avg"] < results["catmullrom"]["phase_avg"]
    print(f"  mitchell {results['mitchell']['phase_avg']:+.4f} < catmullrom "
          f"{results['catmullrom']['phase_avg']:+.4f} : {'PASS' if ok else 'FAIL'}")

    measured = -0.2851  # x2, B0 -> B1
    print(f"\n--- does strehl's gather behave like a Catmull-Rom? ---")
    cr = results["catmullrom"]["phase_avg"]
    print(f"  independent Catmull-Rom, phase-averaged : {cr:+.4f} dex")
    print(f"  strehl B0 -> B1 measured in x2          : {measured:+.4f} dex")
    print(f"  difference                              : {measured - cr:+.4f} dex")

    print("\n--- what a kernel change would buy ---")
    for name in ["lanczos3", "bspline"]:
        gain = results[name]["phase_avg"] - cr
        print(f"  {name:12s} vs catmullrom : {gain:+.4f} dex  "
              f"({10**abs(gain):.3f}x power, {10**(abs(gain)/2):.3f}x amplitude)")

    json.dump(
        dict(baseline=float(base.mean()), phases=phases, results=results, strehl_b0_b1=measured, ordering_ok=bool(ok)),
        open(os.path.join(OUT, "x3_kernel.json"), "w"),
        indent=1,
    )
    print(f"\nwrote {os.path.join(OUT, 'x3_kernel.json')}")


if __name__ == "__main__":
    main()
