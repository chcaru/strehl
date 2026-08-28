"""V-DILUTE Assignment 2 -- where does the base band's contribution live?

The difference between --pyramid-base mean and --pyramid-base weighted at fixed
--pyramid-bands is EXACTLY the base band's contribution difference.  This script
answers ORCH's item 1 directly: does that difference carry energy in the
qualified SIGNAL band (0.17-0.25 cyc/px), or is it confined to tone?

Also audits both rails (clipping AND black) on every master before scoring,
because a structural metric reads CLEAN at either rail.
"""
import sys
import os
import numpy as np
import tifffile
from scipy.ndimage import gaussian_filter

# Same sigma placement as ORCH's contrast_ms.py: a Gaussian of width sigma cuts
# at f = 1/(2*pi*sigma) cyc/px.
SIGMAS = [0.6366, 0.9362, 2.0, 4.0, 8.0, 16.0]
EDGES = [1.0 / (2.0 * np.pi * s) for s in SIGMAS]


def lum(p):
    a = tifffile.imread(p)
    if a.ndim == 3:
        a = a[..., :3].astype(np.float64) @ np.array([0.2126, 0.7152, 0.0722])
    return a.astype(np.float64)


def rails(p):
    """Both rails plus median. A saturated OR blacked master reads CLEAN on
    every structural axis -- Assignment 1 caught one of my own errors here."""
    a = tifffile.imread(p)
    mx = 65535
    return dict(
        clip=100.0 * np.mean(a >= mx),
        black=100.0 * np.mean(a <= 0),
        med=float(np.median(a)),
        p90=float(np.percentile(a, 90)),
    )


def octaves(x):
    out, prev = [], x
    for s in SIGMAS:
        cur = gaussian_filter(x, s)
        out.append(prev - cur)
        prev = cur
    out.append(prev)  # residual: everything below the coarsest cut
    return out


def report(tag, pa, pb):
    print("=" * 78)
    print(f"{tag}")
    print(f"  A = {os.path.basename(pa)}")
    print(f"  B = {os.path.basename(pb)}")

    for nm, p in (("A", pa), ("B", pb)):
        r = rails(p)
        flag = "BLOWN" if r["clip"] > 25 else ("BLACK" if r["black"] > 25 else "ok")
        print(f"  rails {nm}: clip={r['clip']:6.3f}%  black={r['black']:6.3f}%  "
              f"median={r['med']:8.1f}  p90={r['p90']:8.1f}   [{flag}]")

    a, b = lum(pa), lum(pb)
    assert a.shape == b.shape, f"shape mismatch {a.shape} {b.shape}"

    d = b - a
    print(f"  difference: max|d| = {np.abs(d).max():9.1f} DN    "
          f"rms = {d.std():8.3f} DN    mean = {d.mean():+8.2f} DN")
    if np.abs(d).max() == 0:
        print("  >> BIT-IDENTICAL: the flag moved nothing.")
        return None

    # Decompose the DIFFERENCE itself. This is the base band's contribution.
    bd = octaves(d)
    tot = sum(float((x ** 2).sum()) for x in bd)
    print()
    print(f"  {'band':>5s} {'cyc/px':>14s} {'kind':>8s} {'share of |diff| energy':>24s}")
    print("  " + "-" * 56)
    shares = []
    for j in range(len(bd)):
        e = float((bd[j] ** 2).sum())
        sh = 100.0 * e / tot if tot > 0 else 0.0
        shares.append(sh)
        if j < len(SIGMAS):
            hi = 0.5 if j == 0 else EDGES[j - 1]
            lo = EDGES[j]
            rng = f"{lo:.3f}-{hi:.3f}"
        else:
            rng = f"< {EDGES[-1]:.3f}"
        tag_k = {0: "NOISE", 1: "SIGNAL"}.get(j, "")
        bar = "#" * int(round(sh / 2.0))
        print(f"  {j:5d} {rng:>14s} {tag_k:>8s} {sh:21.3f}%  {bar}")

    at_or_above_signal = shares[0] + shares[1]
    print()
    print(f"  >> share of base-band difference energy at/above 0.17 cyc/px "
          f"(NOISE+SIGNAL): {at_or_above_signal:.3f}%")
    print(f"  >> share below 0.010 cyc/px (tone/level region)          : "
          f"{shares[-1]:.3f}%")
    return dict(sig=shares[1], noise=shares[0], tone=shares[-1],
                hi=at_or_above_signal, rms=float(d.std()),
                mx=float(np.abs(d).max()))


if __name__ == "__main__":
    D = r"D:\strehl-out\V-DILUTE\baseband"
    subj = sys.argv[1]
    res = {}
    for b in (7, 2):
        pa = os.path.join(D, f"{subj}.b{b}.mean.tiff")
        pb = os.path.join(D, f"{subj}.b{b}.weighted.tiff")
        if not (os.path.exists(pa) and os.path.exists(pb)):
            print(f"missing arms for bands={b}")
            continue
        role = "SHIPPING DEFAULT" if b == 7 else "POTENCY ARM"
        res[b] = report(f"{subj}  bands={b}  mean vs weighted   [{role}]", pa, pb)
    print("=" * 78)
    if res.get(7) and res.get(2):
        print(f"POTENCY CHECK: signal-band share of the base-band difference")
        print(f"   bands=7 (default): {res[7]['sig']:.3f}%   rms {res[7]['rms']:.3f} DN")
        print(f"   bands=2 (potency): {res[2]['sig']:.3f}%   rms {res[2]['rms']:.3f} DN")
        if res[2]['rms'] > 0:
            print(f"   leverage bands2/bands7 on rms: {res[2]['rms'] / max(res[7]['rms'], 1e-9):.2f}x")
