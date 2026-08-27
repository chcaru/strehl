"""DIAGNOSIS: on a rim-free image, WHICH edges does v4 score above zero?

Not a deliverable.  v4's step gate drove the negative control from +14.85% to
+2.43% but never to zero, and the honest next move is to find out what the
surviving excursions are rather than to keep raising a threshold until the
number looks acceptable.  Tuning a gate against the control until it reads zero,
with no account of WHY, is fitting the instrument to the answer.

Emits, per surviving edge on the smoothed control, the bright statistic
alongside four candidate discriminators, and reports how much of the residual
each one would remove.

    python rimdiag.py [113|119]
"""
import os
import sys

import numpy as np
from scipy import ndimage

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import ffarms                                                    # noqa: E402

R = 12
T = 256


def profiles(g, clip, rois, t, nmax=300, seed=11):
    """v3's profile construction, re-implemented here ONLY so the per-edge
    diagnostics can be emitted alongside; the arithmetic is identical."""
    rng = np.random.default_rng(seed)
    tt = np.arange(-R, R + 1)
    iB = np.where((tt >= 2) & (tt <= 7))[0]
    rows = []
    for (y, x) in rois:
        tile = g[y:y + t, x:x + t]
        if clip[y:y + t, x:x + t].any():
            continue
        sm = ndimage.uniform_filter(tile, 3)
        gy, gx = np.gradient(sm)
        mag = np.hypot(gx, gy)
        ys, xs = np.nonzero(mag > np.percentile(mag, 99.0))
        keep = (ys > R + 2) & (ys < t - R - 2) & (xs > R + 2) & (xs < t - R - 2)
        ys, xs = ys[keep], xs[keep]
        if len(ys) == 0:
            continue
        if len(ys) > nmax:
            i = rng.choice(len(ys), nmax, replace=False)
            ys, xs = ys[i], xs[i]
        for yy, xx in zip(ys, xs):
            d = np.array([gx[yy, xx], gy[yy, xx]])
            n = np.hypot(*d)
            if n < 1e-12:
                continue
            d /= n
            p = tile[np.round(yy + d[1] * tt).astype(int),
                     np.round(xx + d[0] * tt).astype(int)]
            lo, hi = p[:4].mean(), p[-4:].mean()
            step = hi - lo
            if step <= 0:
                continue
            if p[:4].std() > 0.20 * step or p[-4:].std() > 0.20 * step:
                continue
            q = (p - lo) / step
            if abs(q[R] - 0.5) > 0.35:
                continue
            rows.append(dict(
                bright=float(q[iB].max() - 1.0),
                step=float(step),
                # (a) how flat the shoulders really are, in units of step
                flat=float(max(p[:4].std(), p[-4:].std()) / step),
                # (b) flatness over a WIDER shoulder: t=-12..-8 and +8..+12
                flat5=float(max(p[:5].std(), p[-5:].std()) / step),
                # (c) is the core actually a monotone step?
                mono=float(np.min(np.diff(q[R - 2:R + 3]))),
                # (d) does the far shoulder sit where a step says it should?
                #     for a real step, q beyond the transition is ~1 flat;
                #     competing structure shows up as spread between the
                #     inner and outer halves of the plateau
                pl=float(abs(p[-2:].mean() - p[-4:-2].mean()) / step),
            ))
    return rows


def main(argv):
    key = next((a for a in argv if a in ffarms.SUBJECTS), "113")
    arms = ffarms.build(key)
    ref = arms["strehl"]
    grid = ffarms.detail_grid(ref.g, T=T)
    rois = ref.rois_for(grid, T)
    print(f"subject {key}  ROIs {len(rois)}")

    ctrl = ndimage.gaussian_filter(ref.g, 3.0).astype(np.float32)
    rows = profiles(ctrl, ref.clip, rois, ref.tsize(T))
    b = np.array([r["bright"] for r in rows])
    print(f"\nRIM-FREE CONTROL: {len(rows)} edges, median bright "
          f"{np.median(b)*100:+.3f}%")
    print("  A blurred raster cannot overshoot.  Every one of these is the")
    print("  instrument, not the image.")
    qs = [50, 75, 90, 95, 99]
    print("  bright percentiles: " +
          "  ".join(f"p{q}={np.percentile(b,q)*100:+.2f}%" for q in qs))

    print("\n  Where does the residual live?  Median bright by step decile:")
    st = np.array([r["step"] for r in rows])
    order = np.argsort(st)
    for i in range(10):
        s = order[i * len(order) // 10:(i + 1) * len(order) // 10]
        print(f"    step {st[s].min():.4f}..{st[s].max():.4f}  "
              f"n={len(s):>5}  median bright {np.median(b[s])*100:+7.3f}%")

    print("\n  CANDIDATE DISCRIMINATORS.  For each, the control's median")
    print("  bright rim after keeping only edges that pass, and how many")
    print("  survive.  A discriminator is only useful if it drives the")
    print("  control to zero while leaving enough edges to have power.")
    for nm, key_, lo_is_good, cuts in (
        ("shoulder flatness (4 px)", "flat", True, (0.20, 0.10, 0.05, 0.02)),
        ("shoulder flatness (5 px)", "flat5", True, (0.20, 0.10, 0.05, 0.02)),
        ("monotone core min-diff", "mono", False, (-0.10, 0.0, 0.02, 0.05)),
        ("plateau split", "pl", True, (0.20, 0.10, 0.05, 0.02)),
    ):
        v = np.array([r[key_] for r in rows])
        print(f"\n   {nm}")
        for c in cuts:
            m = v <= c if lo_is_good else v >= c
            if m.sum() < 30:
                print(f"     cut {c:+.3f}   n={int(m.sum()):>6}  too few")
                continue
            print(f"     cut {c:+.3f}   n={int(m.sum()):>6}  "
                  f"median bright {np.median(b[m])*100:+7.3f}%")

    print("\n  JOINT: flatness(5 px) <= c AND monotone core >= 0")
    v5 = np.array([r["flat5"] for r in rows])
    mo = np.array([r["mono"] for r in rows])
    for c in (0.10, 0.05, 0.03, 0.02):
        m = (v5 <= c) & (mo >= 0.0)
        print(f"     flat5<={c:.3f} & mono>=0   n={int(m.sum()):>6}  "
              f"median bright "
              f"{np.median(b[m])*100:+7.3f}%" if m.sum() >= 30 else
              f"     flat5<={c:.3f} & mono>=0   n={int(m.sum()):>6}  too few")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
