"""V-BLEND: is there a hard clamp at zero, or a smooth darkening?

The discriminating signature of a CLAMP is a spike of probability mass at
exactly one value. Mass that "wanted" to be negative piles up on the boundary.
A smooth darkening has no such spike: the density at level 0 is about the same
as the density at levels 1, 2, 3.

So the statistic is a PER-LEVEL DENSITY RATIO, not a percentage:

    p0     = fraction of pixels at exactly 0
    dens_W = (fraction in levels 1..W) / W      <- mean per-level density above 0
    spike  = p0 / dens_W

spike ~ 1  means level 0 is unremarkable -> smooth.
spike >> 1 means level 0 holds mass no smooth density would put there -> clamp.

The whole near-zero histogram is printed ABOVE the verdict so a reader can see
the shape rather than trust the scalar. A detector built on a guessed threshold
returns a number that looks the same whether it found nothing or looked nowhere.
"""
import sys
import numpy as np
import tifffile

CH = ("R", "G", "B")


def load(path):
    a = tifffile.imread(path)
    assert a.dtype == np.uint16, f"expected uint16, got {a.dtype}"
    assert a.ndim == 3 and a.shape[2] == 3, f"expected HxWx3, got {a.shape}"
    return a


def census(a, label, W=256, show=(0, 1, 2, 3, 4, 8, 16, 32, 64, 128, 256, 512, 1024)):
    n = a.shape[0] * a.shape[1]
    print(f"\n--- {label}   {a.shape[1]}x{a.shape[0]}  n={n:,} px/channel ---")
    out = {}
    for c in range(3):
        v = a[:, :, c].ravel()
        h = np.bincount(v, minlength=1200)[:1200].astype(np.float64)
        p0 = h[0] / n
        dens = h[1:W + 1].sum() / W / n
        spike = (p0 / dens) if dens > 0 else float("inf")
        cum = np.cumsum(h) / n
        print(f"  {CH[c]}: count@0 = {int(h[0]):>10,}  = {p0*100:8.4f}% of frame")
        print(f"     cumulative %<=lvl : " + "  ".join(
            f"{l}:{cum[l]*100:.4f}" for l in show))
        print(f"     per-level counts  : " + "  ".join(
            f"{l}:{int(h[l]):,}" for l in (0, 1, 2, 3, 4, 5, 10, 20, 50, 100, 200)))
        print(f"     mean per-level density over levels 1..{W} = {dens*100:.6f}% per level")
        print(f"     SPIKE RATIO p0/density = {spike:,.1f}x")
        out[CH[c]] = dict(p0=p0, spike=spike, count0=int(h[0]), dens=dens)
    return out


def verdict(res, label, spike_thresh=20.0, p0_thresh=1e-4):
    print(f"\n  VERDICT for {label}:")
    for c in CH:
        r = res[c]
        if r["p0"] < p0_thresh:
            v = f"no meaningful mass at zero ({r['p0']*100:.4f}%)"
        elif r["spike"] >= spike_thresh:
            v = f"CLAMP  (spike {r['spike']:,.0f}x, {r['p0']*100:.4f}% of frame)"
        else:
            v = f"smooth (spike {r['spike']:.1f}x, {r['p0']*100:.4f}% of frame)"
        print(f"     {c}: {v}")


if __name__ == "__main__":
    for path in sys.argv[1:]:
        a = load(path)
        lab = path.split("\\")[-1]
        r = census(a, lab)
        verdict(r, lab)
        del a
