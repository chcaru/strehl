"""A/B the demosaic on real captures: sharpness, and ringing at hard edges.

Both arms come from ONE binary (SHA256 88DEABFF...45B9), selected at runtime by
STREHL_DEMOSAIC, so no cross-build variable can enter.

Ringing is the hard fail. The detector is an overshoot test at strong edges: for
each edge crossing, take the plateau level on each side from pixels well clear
of the transition, then measure how far the profile excursions go BEYOND the
range spanned by those two plateaux. A monotone edge never leaves that range; a
Gibbs overshoot does, and by how much is the number that decides shippability.
"""
import sys
from pathlib import Path
import numpy as np
import tifffile

PIN = Path(r"C:\dev\strehl-out\BUILD-SHARP\demo-ab")


def load(subj, arm):
    a = tifffile.imread(PIN / f"{subj}--{arm}.tif").astype(np.float64)
    return a


def luma(a):
    return 0.2126 * a[:, :, 0] + 0.7152 * a[:, :, 1] + 0.0722 * a[:, :, 2]


def grad_energy(y):
    gx = np.diff(y, axis=1)[:-1, :]
    gy = np.diff(y, axis=0)[:, :-1]
    return np.hypot(gx, gy)


def edge_overshoot(y, n_cand=40000, half=12, amp_floor=None, seed=3):
    """Max excursion beyond the two plateau levels, as a fraction of edge
    amplitude.

    Returns `(frac_over, p99, n_measured, n_rejected)`. The counts are
    partitioned so that a rejected edge cannot be read as a passing one: the
    first version of this divided by the plateau difference without checking it
    was a real step, and on textured real data reported a p99 "overshoot" of
    336 -- an artifact of dividing by near-zero, not a measurement.

    Edges are the top `n_cand` horizontal gradients, taken by rank rather than
    by a quantile threshold: a quantile degenerates to the maximum when every
    edge in the frame has the same amplitude, which is exactly the case in the
    commissioning image and returned zero edges the first time this was run.

    The plateau windows are the outer 5 samples of the profile, well clear of
    the transition. Sampling them nearer the edge measures the transition
    itself and hides the overshoot inside `amp`.
    """
    h, w = y.shape
    if amp_floor is None:
        lo, hi = np.quantile(y[::11, ::11], [0.001, 0.999])
        amp_floor = 0.05 * (hi - lo)
    gx = np.abs(np.diff(y, axis=1))
    # An edge is a gradient PEAK, not merely a large gradient. Ranking raw
    # gradients admits the shoulders of the same edge, whose profile window
    # straddles the transition instead of spanning it; that is what made the
    # null fail when the candidate cap was raised. Requiring a strict local
    # maximum along the row gives ~one candidate per edge.
    peak = (gx[:, 1:-1] >= gx[:, :-2]) & (gx[:, 1:-1] > gx[:, 2:])
    ys, xs = np.nonzero(peak)
    xs = xs + 1
    keep = (xs > half + 2) & (xs < w - half - 2)
    ys, xs = ys[keep], xs[keep]
    if len(ys) == 0:
        return float("nan"), float("nan"), 0, 0
    vals = gx[ys, xs]
    take = np.argsort(vals)[-min(n_cand, len(vals)):]
    ys, xs = ys[take], xs[take]
    over, rejected = [], 0
    for r, c in zip(ys, xs):
        prof = y[r, c - half:c + half + 2]
        left = np.median(prof[:5])
        right = np.median(prof[-5:])
        lo_p, hi_p = min(left, right), max(left, right)
        amp = hi_p - lo_p
        if amp < amp_floor:
            # Not a step between two plateaux -- texture, or an edge whose
            # profile never settles. Counted, not silently dropped.
            rejected += 1
            continue
        exc = max(prof.max() - hi_p, lo_p - prof.min(), 0.0)
        over.append(exc / amp)
    over = np.array(over)
    if len(over) == 0:
        return float("nan"), float("nan"), 0, rejected
    return (float((over > 0.02).mean()), float(np.quantile(over, 0.99)),
            len(over), rejected)


def commission():
    """The detector must catch a planted overshoot and must not invent one.

    Null: a clean monotone edge, which by construction never leaves the range
    spanned by its own plateaux. Plant: the same edge with a known Gibbs
    overshoot, which the detector must report at the planted size.
    """
    rng = np.random.default_rng(11)
    h, w = 600, 600
    x = np.arange(w)
    # A monotone edge at every row, jittered so edges are not all at one column.
    # The transition is deliberately sharp (scale 0.6 px): a soft edge has not
    # reached its plateau a few pixels out, so a plant placed there is partly
    # absorbed into the plateau and the detector appears to under-recover when
    # in fact the plant was never fully outside the range. That is what the
    # first commissioning run measured.
    base = np.zeros((h, w))
    centres = rng.integers(200, 400, size=h)
    for r in range(h):
        base[r] = 1000.0 + 8000.0 / (1.0 + np.exp(-(x - centres[r]) / 0.6))
    ok = True
    frac, p99, n, rej = edge_overshoot(base, seed=5)
    print(f"  NULL  monotone edge      edges={n:5d} rej={rej:6d}  frac>2% = {frac:.4f}  p99 = {p99:.4f}"
          f"   (want ~0)")
    if not (p99 < 0.02):
        print("  NULL FAILED — the detector reports overshoot on a monotone edge")
        ok = False
    for planted in (0.05, 0.15):
        img = base.copy()
        for r in range(h):
            c = centres[r]
            amp = 8000.0
            img[r, c + 4:c + 7] += planted * amp
            img[r, c - 6:c - 3] -= planted * amp
        frac, p99, n, rej = edge_overshoot(img, seed=5)
        print(f"  PLANT {planted:.0%} overshoot     edges={n:5d}  frac>2% = {frac:.4f}"
              f"  p99 = {p99:.4f}   (want ~{planted:.2f})")
        if not (abs(p99 - planted) < 0.2 * planted and frac > 0.9):
            print(f"  PLANT {planted:.0%} FAILED — detector did not recover the planted size")
            ok = False
    print(f"  commissioning: {'PASS' if ok else 'FAIL'}")
    return ok


def main():
    print("Both arms from one binary, SHA256 88DEABFF7406C6E44A585D0BF72E33CBF353CECCE6AD4A98F8AE058581DB45B9")
    print("Arms differ only by STREHL_DEMOSAIC; alignment cache shared per subject.\n")
    print("Commissioning the ringing detector:")
    if not commission():
        print("INSTRUMENT NOT COMMISSIONED — no result below is trustworthy")
        return 2
    print()
    for subj in ("bee-3-cpl", "tweezers-cpl"):
        try:
            d, m = load(subj, "directional"), load(subj, "malvar")
        except FileNotFoundError as e:
            print(f"{subj}: MISSING {e}")
            continue
        assert d.shape == m.shape, (d.shape, m.shape)
        yd, ym = luma(d), luma(m)
        print(f"=== {subj}  {d.shape} ===")
        print(f"  mean level        malvar {ym.mean():10.1f}   directional {yd.mean():10.1f}"
              f"   ratio {yd.mean()/ym.mean():.5f}")
        gd, gm = grad_energy(yd), grad_energy(ym)
        for q in (0.50, 0.90, 0.99, 0.999):
            a, b = np.quantile(gm, q), np.quantile(gd, q)
            print(f"  gradient p{q*100:<6.1f}  malvar {a:10.2f}   directional {b:10.2f}"
                  f"   ratio {b/max(a,1e-9):.4f}")
        # False colour: saturation on what should be neutral metal.
        for name, arr in (("malvar", m), ("directional", d)):
            mx, mn = arr.max(axis=2), arr.min(axis=2)
            sat = (mx - mn) / np.maximum(mx, 1.0)
            print(f"  chroma spread p99  {name:12s} {np.quantile(sat, 0.99):.5f}")
        for name, yy in (("malvar", ym), ("directional", yd)):
            frac, p99, n, rej = edge_overshoot(yy)
            print(f"  RINGING {name:12s} edges={n:5d} rej={rej:6d}  frac>2% = {frac:.4f}   p99 overshoot = {p99:.4f}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
