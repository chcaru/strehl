"""M113 K9 - STACK-INDEPENDENCE. Is the lanczos3-over-catmull-rom gain a property
of the RESAMPLER, or of bee-3-cpl?

M112 hands over the prediction it did not test: the coverage fix's recovery is
wildly stack-dependent (-0.0330 to +0.1516 across nine stacks), so if the kernel
gain is a real property of the kernel it should be roughly FLAT across the same
nine. And it is the sharper discriminator against the ringing hypothesis than
another ROI on bee-3-cpl, because ringing scales with EDGE DENSITY and bee-3-cpl
is wall-to-wall hairs while foam and flat-on-ruler are not.

This is fact 1420's OWN instrument -- a synthetic sub-pixel phase average over a
single un-resampled frame, pure NumPy, no binary, so it is immune to the
StackIdentity cache defect (fact 1446) by construction. Tiles are chosen
geometrically, before any result is seen (rule 24), and the 40-sharpest
selection M95 used is reported beside it so the choice is visible rather than
load-bearing.

Controls:
  K0 phase 0 must read ~0 for both kernels, or they are not interpolating and
     every other row is measuring the harness.
  KD edge density per stack, so "is the gain tracking edge density" is a number
     rather than an opinion.
"""
import json
import os
import sys

import numpy as np
import tifffile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "experiments", "M95-resample", "src"))
import x2_pairs as X  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "out")
S = r"C:\dev\strehl-out\M113\stacks"
TILE, PAD = 256, 16
PHASES = [i / 8.0 for i in range(1, 8)]      # 7 non-zero phases, as arm 7 used
STACKS = ["bee-3-cpl", "flat-on-ruler-cpl", "tweezers-cpl", "leaf-2-cpl", "foam",
          "lavendar-cpl", "flowers-cpl", "lead-1-cpl", "flower-bud-alone-cpl"]


def cr_w(p):
    o = np.array([-1, 0, 1, 2])
    t = p - o
    a = np.abs(t)
    a2, a3 = a * a, a * a * a
    w = np.where(a <= 1.0, 1.5 * a3 - 2.5 * a2 + 1.0,
                 np.where(a < 2.0, -0.5 * a3 + 2.5 * a2 - 4.0 * a + 2.0, 0.0))
    return w, o


def l3_w(p):
    o = np.array([-2, -1, 0, 1, 2, 3])
    t = p - o
    v = np.sinc(t) * np.sinc(t / 3.0)
    v = np.where(np.abs(t) < 3.0, v, 0.0)
    return v / v.sum(), o


def shift(a, p, wf):
    """Separable gather of `a` at (i+p, j+p). PAD >= 3 keeps roll wrap out of the
    scored interior."""
    w, o = wf(p)
    t = np.zeros_like(a)
    for wi, oi in zip(w, o):
        t += wi * np.roll(a, -int(oi), axis=1)
    r = np.zeros_like(a)
    for wi, oi in zip(w, o):
        r += wi * np.roll(t, -int(oi), axis=0)
    return r


def main():
    res = {}
    print(f"{'stack':22s} {'n':>4s} {'catmull-rom':>12s} {'lanczos3':>10s} "
          f"{'GAIN dex':>10s} {'sem':>7s} {'K0 cr':>8s} {'K0 l3':>8s} {'edge dens':>10s}")
    rows = []
    for name in STACKS:
        p = os.path.join(S, f"{name}-1f.tif")
        img = X.load_luma(p).astype(np.float64)
        h, w = img.shape
        tiles = [(y, x) for y in range(h // 4, 3 * h // 4 - TILE, TILE)
                 for x in range(w // 4, 3 * w // 4 - TILE, TILE)]
        # edge density: fraction of pixels whose gradient exceeds 10% of the
        # frame's dynamic range -- a stand-in for "how many occluding edges"
        sm = img[::4, ::4]
        g = np.hypot(*np.gradient(sm))
        dens = float((g > 0.10 * (np.percentile(sm, 99.5) - np.percentile(sm, 0.5))).mean())
        dc, dl, k0c, k0l = [], [], [], []
        for (y, x) in tiles:
            src = img[y - PAD:y + TILE + PAD, x - PAD:x + TILE + PAD]
            if src.shape != (TILE + 2 * PAD, TILE + 2 * PAD):
                continue
            base = X.band_ratio(src[PAD:-PAD, PAD:-PAD], 1.0)
            k0c.append(X.band_ratio(shift(src, 0.0, cr_w)[PAD:-PAD, PAD:-PAD], 1.0) - base)
            k0l.append(X.band_ratio(shift(src, 0.0, l3_w)[PAD:-PAD, PAD:-PAD], 1.0) - base)
            vc = [X.band_ratio(shift(src, ph, cr_w)[PAD:-PAD, PAD:-PAD], 1.0) - base
                  for ph in PHASES]
            vl = [X.band_ratio(shift(src, ph, l3_w)[PAD:-PAD, PAD:-PAD], 1.0) - base
                  for ph in PHASES]
            dc.append(np.mean(vc))
            dl.append(np.mean(vl))
        dc, dl = np.array(dc), np.array(dl)
        d = dl - dc
        sem = float(d.std(ddof=1) / np.sqrt(d.size))
        print(f"{name:22s} {d.size:4d} {dc.mean():+12.4f} {dl.mean():+10.4f} "
              f"{d.mean():+10.4f} {sem:7.4f} {np.mean(k0c):+8.4f} {np.mean(k0l):+8.4f} "
              f"{dens:10.4f}")
        rows.append((name, float(dc.mean()), float(dl.mean()), float(d.mean()), sem,
                     float(np.mean(k0c)), float(np.mean(k0l)), dens))
        res[name] = dict(n=int(d.size), cr=float(dc.mean()), l3=float(dl.mean()),
                         gain=float(d.mean()), sem=sem, k0_cr=float(np.mean(k0c)),
                         k0_l3=float(np.mean(k0l)), edge_density=dens)

    g = np.array([r[3] for r in rows])
    e = np.array([r[7] for r in rows])
    k0 = np.array([abs(r[5]) for r in rows] + [abs(r[6]) for r in rows])
    print(f"\nK0 phase-0 null, worst over all stacks and both kernels: {k0.max():.5f} dex")
    print(f"   (both kernels interpolate; anything large here would void the table)")
    print(f"\nGAIN across nine stacks: mean {g.mean():+.4f}  sd {g.std(ddof=1):.4f}  "
          f"min {g.min():+.4f}  max {g.max():+.4f}  range {g.max()-g.min():.4f}")
    print(f"   coefficient of variation {g.std(ddof=1)/g.mean():.3f}")
    print(f"   M112's coverage recovery over the SAME nine: range 0.1846 "
          f"(-0.0330 .. +0.1516)")
    print(f"   ratio of spreads, kernel : coverage = "
          f"{(g.max()-g.min())/0.1846:.3f}")
    print(f"\ncorr(edge density, gain) = {np.corrcoef(e, g)[0,1]:+.4f}")
    print("   a ringing artefact would track edge density; a kernel property would not.")
    res["_summary"] = dict(mean=float(g.mean()), sd=float(g.std(ddof=1)),
                           min=float(g.min()), max=float(g.max()),
                           range=float(g.max() - g.min()),
                           cv=float(g.std(ddof=1) / g.mean()),
                           corr_edge_density=float(np.corrcoef(e, g)[0, 1]),
                           k0_worst=float(k0.max()))
    json.dump(res, open(os.path.join(OUT, "k9_stacks.json"), "w"), indent=1)
    print(f"\nwrote {os.path.join(OUT, 'k9_stacks.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())