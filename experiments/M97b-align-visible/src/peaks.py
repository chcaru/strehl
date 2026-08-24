"""R4 -- a sharpness metric that ranks the visibly sharper render higher.

WHY A PERCENTILE AND NOT A MEAN. R1 (mech1.py) measured, on synthetic data
where the truth is not in dispute:

    case       tenengrad   peak|grad|
    single       7812.50       1000.0
    doubled      3906.25        500.0   (0.5000x -- doubling HALVES tenengrad)
    blurred      2654.95        375.5

Both functionals are monotone in sharpness on an isolated edge. The difference
is what happens to the REST of the frame. Mean-of-squares is an average over
every pixel, so it is dominated by the ~99% of a macro frame that carries no
fine detail, and bands.py measured that this is exactly where the null wins:
in the flattest quartile the aligned render reads 0.6303, because
misregistration drags real structure across regions that should be smooth and
mean gradient energy counts displaced structure as detail.

A high percentile of |grad| ignores the bulk entirely and asks only how sharp
the sharpest transitions in the frame are. R1 shows that quantity falls under
both doubling and blur, and noise cannot raise it because noise gradients are
small next to a real edge.

THE PRE-REGISTERED BAR (PREREG2 R4), stated before this was run:
  * treatment must read > 1.00 for aligned vs zoomnull on bee-3
  * placebo (self vs self) must read 1.000 +/- 0.005
  * blur plant (sigma=1.0) must read > 1.30
  * DIRECTION PLANT: blurred(aligned) vs untouched null must read < 1.00.
    A metric that prefers the aligned arm unconditionally is not an
    instrument, it is a thumb on the scale.
"""

import json
import sys

import numpy as np
import tifffile
from scipy.ndimage import gaussian_filter

PCTS = [50.0, 90.0, 99.0, 99.9, 99.99]


def load(path):
    a = tifffile.imread(path)
    assert a.dtype == np.uint16, f"{path}: expected uint16, got {a.dtype}"
    g = a[:, :, 1] if a.ndim == 3 else a
    return g.astype(np.float32)


def grad_mag(g):
    gx = np.zeros_like(g)
    gy = np.zeros_like(g)
    gx[:, 1:-1] = g[:, 2:] - g[:, :-2]
    gy[1:-1, :] = g[2:, :] - g[:-2, :]
    return np.sqrt(gx * gx + gy * gy)


def stats(g):
    m = grad_mag(g)
    v = np.percentile(m, PCTS)
    flat = m.ravel()
    k = max(1, int(flat.size * 0.0001))
    topk = float(np.mean(np.partition(flat, -k)[-k:]))
    return dict(zip([f"p{p:g}" for p in PCTS], [float(x) for x in v]),
                topk_0p01pct=topk, mean_sq=float((m * m).mean()))


def compare(a, z, label, rows):
    sa, sz = stats(a), stats(z)
    r = {k: (sa[k] / sz[k] if sz[k] else float("nan")) for k in sa}
    rows.append(dict(label=label, a=sa, b=sz, ratio=r))
    print(f"\n--- {label} ---")
    for k in sa:
        print(f"    {k:<14} A {sa[k]:12.2f}  B {sz[k]:12.2f}  A/B {r[k]:.4f}")
    return r


def main(argv):
    d = r"C:\dev\strehl-out\M86-align"
    a = load(rf"{d}\bee-3-ALIGNED.tif")
    z = load(rf"{d}\bee3-zoomnull.tif")
    assert a.shape == z.shape, "arms are not FOV-matched"
    print("dims", a.shape)

    rows = []
    print("=== CONTROLS (these decide whether the treatment is admissible) ===")
    compare(z, z, "PLACEBO zoomnull vs itself (want 1.0000)", rows)
    compare(z, gaussian_filter(z, 1.0),
            "PLANT zoomnull vs blurred(zoomnull) (want > 1.30)", rows)
    dirp = compare(gaussian_filter(a, 1.0), z,
                   "DIRECTION PLANT blurred(aligned) vs zoomnull (want < 1.00)",
                   rows)

    print("\n=== TREATMENT (visual ground truth: aligned IS sharper) ===")
    tre = compare(a, z, "aligned vs zoomnull", rows)

    print("\n=== VERDICT against the pre-registered bar ===")
    for k in ("p99", "p99.9", "p99.99", "topk_0p01pct", "mean_sq"):
        ok = tre[k] > 1.0
        dp = dirp[k] < 1.0
        print(f"  {k:<14} treatment {tre[k]:.4f} {'PASS' if ok else 'FAIL'}"
              f"   direction-plant {dirp[k]:.4f} {'PASS' if dp else 'FAIL'}")

    json.dump(rows, open(argv[1], "w"), indent=1)
    print("\nwrote", argv[1])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
