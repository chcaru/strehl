"""M60 — class-level results. Power first, then hypotheses.

Order is fixed: the population of every cell class is asserted and printed
BEFORE any hit rate is read (fact 779). The unit of analysis is the CELL, not
the pixel: pixels inside one cell share a scene, a limb and a noise realisation
and are nowhere near independent, so a per-pixel n of 36000 is not 36000
independent observations. Per-cell medians are compared across classes with a
rank test whose n is the number of cells.
"""

import os
import sys
import json
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cells import CELLS  # noqa: E402
import importlib
A = importlib.import_module("12-analyse")
D16 = importlib.import_module("16-distance")

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, "..", "data"))
TOL = 6
DENS = (1, 2, 4, 8, 13)     # 299 -> 299,150,75,38,23 frames


def mannwhitney(a, b):
    from scipy.stats import mannwhitneyu
    if len(a) < 2 or len(b) < 2:
        return float("nan"), float("nan")
    u, p = mannwhitneyu(a, b, alternative="two-sided")
    return float(u / (len(a) * len(b))), float(p)


if __name__ == "__main__":
    cells = []
    for stack, name, cls, y0, y1, x0, x1 in CELLS:
        d = A.load(stack, name)
        nd = A.load(stack, name, A.NUL)
        if d is None or nd is None:
            continue
        cells.append((stack, name, cls, d, nd))

    print("=" * 78)
    print("POWER  -- asserted before any result is read (fact 779)")
    print("=" * 78)
    counts = {}
    for stack, name, cls, d, nd in cells:
        lab = d["lab"]
        counts.setdefault(cls, []).append(int((lab == 0).sum()))
    for cls, v in sorted(counts.items()):
        print("  class %-9s  cells=%2d   band pixels per cell: min %d  median %d  total %d"
              % (cls, len(v), min(v), int(np.median(v)), sum(v)))
    ncell = {k: len(v) for k, v in counts.items()}
    print("\n  The unit of analysis is the CELL. With %d occ vs %d ctl cells a"
          % (ncell.get("occ", 0), ncell.get("ctl", 0)))
    print("  two-sided Mann-Whitney can reach p<0.05 only if the distributions")
    print("  barely overlap; the smallest detectable shift is roughly a full")
    print("  separation of the two per-cell medians.")
    print("  Within a cell, %d band pixels resolve a hit rate to +-%.2f%% (binomial,"
          % (int(np.median(counts.get('occ', [36000]))),
             100 * 1.96 * np.sqrt(0.25 / np.median(counts.get('occ', [36000])))))
    print("  ignoring spatial correlation, which makes the true interval wider).")

    print()
    print("=" * 78)
    print("H1  does the second peak clear the calibrated noise floor?")
    print("    z* set per cell at 1%% FPR on that cell's own noise-only null")
    print("=" * 78)
    rows = []
    for stack, name, cls, d, nd in cells:
        F, S, lab = d["F"], d["S"], d["lab"]
        real = A.detect(F, S)
        nul = A.detect(nd["F"], nd["S"])
        band = lab == 0
        zst = float(np.percentile(nul["z"][band], 99))
        hit = float(np.mean(real["z"][band] > zst))
        nhit = float(np.mean(nul["z"][band] > zst))
        Ib = d["Ibar"]
        dm = D16.distance_map(Ib)
        dist = dm.ravel()[d["sel"]] if dm is not None else np.zeros(len(d["sel"]))
        kbg = float(np.median(real["k1"][lab == 2])) if (lab == 2).any() else float("nan")
        kfg = float(np.median(real["k1"][lab == 1])) if (lab == 1).any() else float("nan")
        k2 = real["k2"][band].astype(float)
        near_bg = float(np.mean(np.abs(k2 - kbg) <= TOL))
        near_fg = float(np.mean(np.abs(k2 - kfg) <= TOL))
        T = np.median(S, axis=0)
        H, BM = A.entropy_and_boundary(F, T)
        rows.append(dict(stack=stack, cell=name, cls=cls, n=int(F.shape[0]),
                         npx=int(band.sum()), zstar=zst, hit=hit, null_hit=nhit,
                         prom=float(np.median(real["prom"][band])),
                         den=float(np.median(real["denom"][band])),
                         sep=float(np.median(np.abs(real["k2"][band].astype(float)
                                                    - real["k1"][band]))),
                         k_fg=kfg, k_bg=kbg, depth_step=abs(kfg - kbg),
                         near_bg=near_bg, near_fg=near_fg,
                         H=float(np.median(H[band])),
                         bmass=float(np.median(BM[band])),
                         bmass_p90=float(np.percentile(BM[band], 90)),
                         dist_med=float(np.median(dist[band]))))
        print("  %-16s %-18s %-8s n=%3d  hit %5.1f%%  null %4.1f%%  z* %5.2f  "
              "sep %5.1f  |k_fg-k_bg| %5.1f  k2~k_bg %5.1f%%"
              % (stack, name, cls, F.shape[0], 100 * hit, 100 * nhit, zst,
                 rows[-1]["sep"], rows[-1]["depth_step"], 100 * near_bg), flush=True)

    print()
    for cls in ("occ", "occ_flat", "ctl"):
        v = [r["hit"] for r in rows if r["cls"] == cls]
        print("  class %-9s  n_cells=%2d  hit rate median %5.1f%%  range %5.1f-%5.1f%%"
              % (cls, len(v), 100 * np.median(v), 100 * min(v), 100 * max(v)))
    occ = [r["hit"] for r in rows if r["cls"] == "occ"]
    flat = [r["hit"] for r in rows if r["cls"] == "occ_flat"]
    ctl = [r["hit"] for r in rows if r["cls"] == "ctl"]
    for a, b, an, bn in ((occ, ctl, "occ", "ctl"), (occ, flat, "occ", "occ_flat"),
                         (flat, ctl, "occ_flat", "ctl")):
        auc, p = mannwhitney(a, b)
        print("  %-9s vs %-9s : AUC %.3f  p=%.4g" % (an, bn, auc, p))

    print()
    print("  n-matched: only cells with n=299")
    for cls in ("occ", "occ_flat", "ctl"):
        v = [r["hit"] for r in rows if r["cls"] == cls and r["n"] == 299]
        if v:
            print("    %-9s n_cells=%2d  median %5.1f%%" % (cls, len(v), 100 * np.median(v)))

    print()
    print("=" * 78)
    print("H3  is the second peak AT THE BACKGROUND'S FOCUS FRAME?")
    print("    k_bg is the median argmax of the cell's PALE INTERIOR pixels --")
    print("    a different pixel set from the band, so this is not circular.")
    print("=" * 78)
    for cls in ("occ", "occ_flat", "ctl"):
        v = [r for r in rows if r["cls"] == cls]
        print("  %-9s  |k_fg-k_bg| median %5.1f   k2 within %d frames of k_bg: "
              "median %5.1f%%   of k_fg: %5.1f%%"
              % (cls, np.median([r["depth_step"] for r in v]), TOL,
                 100 * np.median([r["near_bg"] for r in v]),
                 100 * np.median([r["near_fg"] for r in v])))
    # permuted pairing null: score each cell's band against ANOTHER cell's k_bg
    rng = np.random.default_rng(4)
    perm = []
    for stack, name, cls, d, nd in cells:
        real = A.detect(d["F"], d["S"])
        band = d["lab"] == 0
        k2 = real["k2"][band].astype(float)
        others = [r for r in rows if r["cls"] == cls and r["cell"] != name
                  and r["n"] == d["F"].shape[0]]
        if not others:
            continue
        o = others[rng.integers(len(others))]
        perm.append((cls, float(np.mean(np.abs(k2 - o["k_bg"]) <= TOL))))
    for cls in ("occ", "occ_flat", "ctl"):
        v = [p for c, p in perm if c == cls]
        if v:
            print("  %-9s  permuted pairing (another cell's k_bg): median %5.1f%%"
                  % (cls, 100 * np.median(v)))

    print()
    print("=" * 78)
    print("N5  mass at the stack boundary -- the 'ran out of frames' diagnosis")
    print("=" * 78)
    for cls in ("occ", "occ_flat", "ctl"):
        v = [r["bmass"] for r in rows if r["cls"] == cls]
        w = [r["bmass_p90"] for r in rows if r["cls"] == cls]
        print("  %-9s  posterior mass in the outer 5%% of frames: median %.4f  p90 %.4f"
              % (cls, np.median(v), np.median(w)))

    print()
    print("=" * 78)
    print("frame-density sweep: the same cells, thinned along the focus axis")
    print("=" * 78)
    sweep = []
    for stack, name, cls, d, nd in cells:
        if d["F"].shape[0] != 299:
            continue
        line = []
        for st in DENS:
            F = np.ascontiguousarray(d["F"][::st])
            S = np.ascontiguousarray(d["S"][::st])
            Fn = np.ascontiguousarray(nd["F"][::st])
            Sn = np.ascontiguousarray(nd["S"][::st])
            band = d["lab"] == 0
            r = A.detect(F, S)
            nn = A.detect(Fn, Sn)
            zst = float(np.percentile(nn["z"][band], 99))
            line.append((F.shape[0], float(np.mean(r["z"][band] > zst)),
                         float(np.median(np.abs(r["k2"][band].astype(float)
                                                - r["k1"][band])))))
        sweep.append(dict(cell=name, cls=cls, line=line))
        print("  %-18s %-8s  " % (name, cls)
              + "  ".join("n=%3d hit %5.1f%% sep %5.1f" % (a, 100 * b, c) for a, b, c in line),
              flush=True)

    with open(os.path.join(DATA, "18-classes.json"), "w", encoding="utf-8") as fh:
        json.dump(dict(rows=rows, sweep=sweep, perm=perm), fh, indent=1)
    print("\nwrote data/18-classes.json")
