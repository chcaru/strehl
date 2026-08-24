"""M70 s23 - is the heavy tail the PSF, or is it the SCENE?

s21 read R10_50 = 2.43-2.70 on the three bee stacks, reproducing across three
separate captures, and s22 showed the estimator's bias at those curve widths is
only +0.010..+0.026 - so the reading is real. But s22 also showed the statistic
cannot separate a Gaussian from a sech2 below w50 = 3.6 frames, and the whole
corpus sits at w50 = 1.6-3.6. A reading of 2.65 is far beyond any smooth
unimodal tail family the estimator could be confusing for a Gaussian.

That points at a specific mechanism, and it is not tail weight:

    w(0.10) is inflated by MULTIMODALITY. A patch spanning two depths has a
    second lobe. At 0.50 of peak the half-width sees only the primary lobe; at
    0.10 of peak it can reach across the valley into the secondary one, and the
    ratio jumps. The curve is not heavy-tailed - it is two curves.

That is exactly M25's question 33 ("is the real defocus growth non-linear in
frame index, OR IS THE SUBJECT'S DEPTH RANGE DOING THE WORK?"), which M67's
instruction (b) named as the thing to separate. The named pairing cannot do it
(109MSDCF has no power). This can, by a different route: a plant with a
SYMMETRIC, GAUSSIAN-BY-CONSTRUCTION PSF over two depths, plus a direct lobe
count on the real curves.

Three arms:
  A  two-depth plant, separation swept wide enough to matter. If a symmetric
     Gaussian PSF over two depths reaches the bees' reading, the reading is
     scene geometry and NOT a PSF property.
  B  direct lobe count on the real corpus curves. If the heavy stacks have
     more lobes, the mechanism is confirmed on real data, not just in a plant.
  C  the association between the two, across all twelve stacks.
"""

from __future__ import annotations

import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import s20_shape_controls as S20  # noqa: E402
import s21_shape_corpus as S21  # noqa: E402
import s22_estimator_floor as S22  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")
G = S20.GAUSS["R10_50"]


def smooth121(s):
    s = np.asarray(s, dtype=np.float64)
    if s.size < 3:
        return s
    o = s.copy()
    o[1:-1] = (s[:-2] + 2.0 * s[1:-1] + s[2:]) / 4.0
    return o


def n_lobes(curve, frac=0.10):
    """Local maxima of the smoothed curve standing above `frac` of the peak."""
    s = smooth121(curve)
    pk = float(np.nanmax(s))
    if not np.isfinite(pk) or pk <= 0:
        return 0
    thr = frac * pk
    n = 0
    for i in range(1, s.size - 1):
        if s[i] > thr and s[i] >= s[i - 1] and s[i] > s[i + 1]:
            n += 1
    return n


def two_depth_curve(K, w50, sep, w_far):
    """Two GAUSSIAN lobes, identical symmetric width, separated by `sep` frames."""
    sigma = w50 / math.sqrt(2.0 * math.log(2.0))
    x = np.arange(K, dtype=np.float64)
    a = np.exp(-0.5 * ((x - (K // 2)) / sigma) ** 2)
    b = np.exp(-0.5 * ((x - (K // 2 + sep)) / sigma) ** 2)
    return (1.0 - w_far) * a + w_far * b


def hdr(t):
    print("\n" + "=" * 118)
    print(t)
    print("=" * 118)


def main() -> None:
    res = {"gauss": G}

    hdr("ARM A - two GAUSSIAN lobes, symmetric by construction. Sweep the separation.")
    print("  The PSF here IS a Gaussian. Every departure from 1.8226 is scene depth.")
    print("  w50 = 2.9 frames, matching the bee stacks (2.86 / 3.57 / 3.46).")
    print(f"\n{'sep':>6}{'w_far':>8}{'R10_50':>10}{'vs G':>9}{'lobes':>8}"
          f"{'reaches bees 2.43-2.70?':>26}")
    res["two_depth"] = []
    for sep in (0, 2, 4, 6, 8, 12, 16, 24):
        for wf in (0.30, 0.50):
            c = two_depth_curve(201, 2.9, sep, wf)
            v = S20.widths(c)["R10_50"]
            nl = n_lobes(c)
            hit = "YES" if 2.43 <= v <= 2.75 else ("over" if v > 2.75 else "")
            res["two_depth"].append({"sep": sep, "w_far": wf, "R10_50": float(v),
                                     "lobes": nl})
            print(f"{sep:>6}{wf:>8.2f}{v:>10.4f}{v - G:>+9.4f}{nl:>8}{hit:>26}")
    mx = max(r["R10_50"] for r in res["two_depth"])
    print(f"\n  A SYMMETRIC GAUSSIAN PSF over two depths reaches R10_50 = {mx:.4f}.")
    print(f"  The bee stacks read 2.43-2.70. Scene depth alone "
          f"{'FULLY ACCOUNTS FOR' if mx >= 2.43 else 'does not reach'} that.")
    res["two_depth_max"] = float(mx)

    hdr("ARM B - direct lobe count on the REAL corpus curves")
    print("  Lobes = local maxima above 0.10 of peak in the [1,2,1]-smoothed curve.")
    print("  If the mechanism is multimodality, the heavy stacks carry more lobes.")
    print(f"\n{'stack':<16}{'R10_50':>9}{'mean lobes':>12}{'% multi':>9}"
          f"{'% >=3 lobes':>13}{'n':>6}")
    res["lobes"] = {}
    rows = []
    for st in S21.S16.STACKS:
        cs, _K = S21.stack_curves(st)
        nl = np.array([n_lobes(c) for c in cs], dtype=np.float64)
        r10 = S22.CORPUS_R10[st]
        e = {"R10_50": r10, "mean_lobes": float(nl.mean()),
             "pct_multi": float(100 * (nl >= 2).mean()),
             "pct_3plus": float(100 * (nl >= 3).mean()), "n": int(nl.size)}
        res["lobes"][st] = e
        rows.append((st, r10, e["mean_lobes"], e["pct_multi"]))
        print(f"{st:<16}{r10:>9.4f}{e['mean_lobes']:>12.2f}{e['pct_multi']:>8.1f}%"
              f"{e['pct_3plus']:>12.1f}%{e['n']:>6}")

    hdr("ARM C - association across the twelve stacks")
    r = np.array([x[1] for x in rows])
    lb = np.array([x[2] for x in rows])
    pm = np.array([x[3] for x in rows])

    def pear(a, b):
        a, b = a - a.mean(), b - b.mean()
        return float((a * b).sum() / math.sqrt((a * a).sum() * (b * b).sum()))

    def spear(a, b):
        ra = np.argsort(np.argsort(a)).astype(float)
        rb = np.argsort(np.argsort(b)).astype(float)
        return pear(ra, rb)

    print(f"  corr(mean lobes, R10_50)   Pearson {pear(lb, r):+.3f}   "
          f"Spearman {spear(lb, r):+.3f}   n=12")
    print(f"  corr(% multi-lobed, R10_50) Pearson {pear(pm, r):+.3f}   "
          f"Spearman {spear(pm, r):+.3f}   n=12")
    res["corr"] = {"lobes_pearson": pear(lb, r), "lobes_spearman": spear(lb, r),
                   "pctmulti_pearson": pear(pm, r), "pctmulti_spearman": spear(pm, r)}

    lo = [x[0] for x in rows if x[1] < 1.95]
    hi = [x[0] for x in rows if x[1] >= 2.0]
    llo = np.mean([res["lobes"][s]["mean_lobes"] for s in lo])
    lhi = np.mean([res["lobes"][s]["mean_lobes"] for s in hi])
    print(f"\n  near-Gaussian stacks (R10_50 < 1.95, n={len(lo)}): mean lobes {llo:.2f}")
    print(f"  heavy stacks         (R10_50 >= 2.0, n={len(hi)}): mean lobes {lhi:.2f}")
    print(f"  ratio {lhi / llo:.2f}x")
    res["split"] = {"low": lo, "high": hi, "lobes_low": float(llo),
                    "lobes_high": float(lhi), "ratio": float(lhi / llo)}

    hdr("ARM D - the two questions are separable: does the SAME patch set carry both?")
    print("  Within the three bee captures - same rig, same subject, three shoots -")
    print("  does the lobe count reproduce the way R10_50 did, and the way the")
    print("  asymmetry statistic A50 did NOT (section 16.7: +0.042 / -0.036 / -0.070)?")
    for st in ("bee-1", "bee-2", "bee-3", "wrapped-text-1", "wrapped-text-2"):
        e = res["lobes"][st]
        print(f"    {st:<16} R10_50 {e['R10_50']:.4f}   mean lobes {e['mean_lobes']:.2f}"
              f"   multi {e['pct_multi']:.1f}%")
    bl = [res["lobes"][s]["mean_lobes"] for s in ("bee-1", "bee-2", "bee-3")]
    br = [res["lobes"][s]["R10_50"] for s in ("bee-1", "bee-2", "bee-3")]
    print(f"\n    bee lobe counts spread {max(bl) / min(bl):.3f}x ; "
          f"bee R10_50 spread {max(br) / min(br):.3f}x")
    print("    (section 16.7's A50 on these same three captures CHANGED SIGN.)")
    res["bee_repro"] = {"lobes_spread": float(max(bl) / min(bl)),
                        "r10_spread": float(max(br) / min(br))}

    with open(os.path.join(OUT, "s23_multimodality.json"), "w") as f:
        json.dump(res, f, indent=1)
    print("\nwrote out/s23_multimodality.json")


if __name__ == "__main__":
    main()
