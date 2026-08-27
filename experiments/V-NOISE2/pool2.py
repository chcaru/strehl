"""pool2.py -- the pre-registered heterogeneity test, and pooling only if it
passes.

PREREGISTRATION.md sec.6, implemented literally and with nothing added:

  1. compute the four per-subject ratios and their CIs
  2. SPLIT TEST, decided in advance.  Heterogeneous if the highest and lowest
     point estimates have NON-OVERLAPPING 95% CIs, or if the rank order of the
     four ratios matches the rank order of `avg_index` with all four subjects
     agreeing in direction.
  3. heterogeneous -> pooling is ILLEGITIMATE.  No pooled headline.  The
     per-subject numbers and the regime split are the result.  A pooled figure
     may still be shown, labelled descriptive only.
  4. homogeneous -> pool as the UNWEIGHTED median of per-subject medians, with
     a bootstrap resampling SUBJECTS AND TILES, so the CI carries
     between-subject variance rather than pretending four scenes are one large
     sample.  Unweighted, so a 299-frame subject cannot outvote a 33-frame one
     on tile count.

sec.6 says why the rule is fixed here rather than after the numbers arrive: a
pooled mean weighted by tile count would let the deepest stack carry the
verdict, and the deepest stack is the one this lane expected to win.

sec.7's falsification conditions are evaluated here too, because they are
statements about the SET of subjects and no per-subject script can see them:

  * >=2 of 4 subjects reading LEVEL or NOISIER on chroma falsifies "strehl is
    cleaner than enfuse" as a general claim
  * a TONE arm that explains a subject's ratio withdraws that subject
  * a QUANT8 arm returning exactly 1.000 blocks that subject

`avg_index` is measured here from strehl's own stack logs -- the `averaged :`
line, mean over all but the last band, following corpus_softness.py:98-104,181.
It is NOT numerically comparable to V-EYES's published values, which are
13-frame subsamples; it is measured consistently across these four and used
only for the RANK test, which is invariant to that.

Usage:  python pool2.py [nboot]
"""
import json
import os
import re
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "..", "V-NOISE"))
from noisefree import boot                                        # noqa: E402
from hd2 import SUBJECTS, ROOT                                     # noqa: E402

CHAN = ["luma  Y", "chroma R-Y", "chroma B-Y"]
LOGS = {"113": None}          # 113's logs live where M127 left them


def avg_index(key):
    """mean(bands[:-1]) of the `averaged :` line in strehl's stack log."""
    cands = [os.path.join(ROOT, key, "logs", "stack-A.log"),
             os.path.join(ROOT, key, "logs", "stack-B.log")]
    if key == "113":
        # the arm measured is 113-A-g1.tiff, so its own stack log is the one
        # that describes it; the g0 / full logs are different merges.
        cands = [r"C:\dev\strehl-out\V-H2H2\logs\113-A-g1.log",
                 r"C:\dev\strehl-out\V-H2H2\logs\113-B-g1.log"]
    for p in cands:
        if not os.path.exists(p):
            continue
        with open(p, encoding="utf-8", errors="replace") as fh:
            for ln in fh:
                if "averaged" in ln and "%" in ln:
                    b = [float(v) for v in re.findall(r"([\d.]+)%", ln)]
                    if len(b) >= 2:
                        return float(np.mean(b[:-1])), p
    return None, None


def boot_pair(num, den, nboot, rng):
    """M127's statistic, IMPORTED not restated: the median of paired per-ROI
    ratios with a bootstrap CI over ROIs.

    A first version of this file computed median(num)/median(den) instead and
    read 1.626 on 113/enfuse where hd2.py reads 1.540.  Two numbers for one
    quantity, from one lane, in one night.  That is exactly the drift the
    import discipline exists to prevent, and it was caught only because 113 is
    a subject whose answer was already known.
    """
    m, lo, hi, _ = boot(num, den, nboot, rng)
    return m, lo, hi


def main():
    nboot = 2000
    for a in sys.argv[1:]:
        if a.isdigit():
            nboot = int(a)
    rng = np.random.default_rng(6)

    subs, missing = {}, []
    for key in SUBJECTS:
        npz = os.path.join(ROOT, key, "hd.npz")
        jsn = os.path.join(ROOT, key, "hd.json")
        if not (os.path.exists(npz) and os.path.exists(jsn)):
            missing.append(key)
            continue
        z = np.load(npz)
        with open(jsn, encoding="utf-8") as fh:
            j = json.load(fh)
        ai, src = avg_index(key)
        subs[key] = {"z": z, "j": j, "avg_index": ai, "ai_src": src}

    print("=" * 100)
    print("V-NOISE2 POOLING -- sec.6 split test first, pooled number only if it passes")
    print("=" * 100)
    if missing:
        print(f"  NOT YET BUILT: {', '.join(missing)} -- reported as absent, "
              f"not dropped.  The subject list is CLOSED (sec.1) and a subject\n"
              f"  that fails to build is a failed subject, not a subject that "
              f"never existed.")
    if len(subs) < 2:
        raise SystemExit("  fewer than two subjects available; nothing to pool")

    print(f"\n{'subject':10s} {'name':22s} {'n':>4s} {'depth':>7s} "
          f"{'regime':>10s} {'tiles':>6s} {'avg_index':>10s}  commissioning")
    for k, s in subs.items():
        m = SUBJECTS[k]
        c = s["j"]["commissioning"]
        ai = s["avg_index"]
        print(f"{k:10s} {m['name']:22s} {m['n']:4d} {m['depth']:>7s} "
              f"{m['regime']:>10s} {s['j']['n_tiles']:6d} "
              f"{(f'{ai:10.2f}' if ai is not None else '         ?')}  "
              f"{'ALL PASS' if c['all_pass'] else 'FAILED'}")

    # ---------------------------------------------------------- sec.7 gates
    print("\n" + "-" * 100)
    print("sec.7 falsification gates, evaluated over the SET")
    print("-" * 100)
    blocked = []
    for k, s in subs.items():
        c = s["j"]["commissioning"]
        for kk, v in c["tone_explained"].items():
            if v >= 0.50:
                blocked.append((k, f"TONE {kk} explains {v * 100:.1f}%"))
        for i, q in enumerate(c["quant8_ratio"]):
            if abs(q - 1.0) < 1e-9:
                blocked.append((k, f"QUANT8 exactly 1.000 on {CHAN[i]}"))
    if blocked:
        for k, why in blocked:
            print(f"  BLOCKED  {k}: {why}")
    else:
        print("  no subject blocked by TONE or QUANT8")

    # ------------------------------------------------- per-subject, per-arm
    res = {}
    for arm in ("enfuse", "fs15-coh"):
        print("\n" + "=" * 100)
        print(f"ARM: {arm}   (>1 = comparator noisier than strehl)")
        print("=" * 100)
        print(f"{'subject':10s} " + " ".join(f"{c:>26s}" for c in CHAN))
        per = {}
        for k, s in subs.items():
            z = s["z"]
            ok = z["ok"]
            if f"shift_{arm}" not in z:
                continue
            row, vals = f"{k:10s} ", []
            for i in range(3):
                num = z[f"shift_{arm}"][ok, i]
                den = z["shift_strehl"][ok, i]
                m, lo, hi = boot_pair(num, den, nboot, rng)
                vals.append((m, lo, hi, num, den))
                row += f"  {m:7.3f} [{lo:6.3f},{hi:6.3f}]"
            print(row)
            per[k] = vals
        res[arm] = per

        # ------------------------------------------- sec.6 step 2, split test
        print(f"\n  SPLIT TEST for {arm} (sec.6 step 2)")
        het_any = False
        for i in range(3):
            pts = {k: v[i][0] for k, v in per.items()}
            hi_k = max(pts, key=pts.get)
            lo_k = min(pts, key=pts.get)
            a_lo, a_hi = per[hi_k][i][1], per[hi_k][i][2]
            b_lo, b_hi = per[lo_k][i][1], per[lo_k][i][2]
            overlap = not (a_lo > b_hi or b_lo > a_hi)
            het_any |= not overlap
            print(f"    {CHAN[i]:11s} extremes {lo_k}={pts[lo_k]:.3f} "
                  f"[{b_lo:.3f},{b_hi:.3f}] vs {hi_k}={pts[hi_k]:.3f} "
                  f"[{a_lo:.3f},{a_hi:.3f}]  -> "
                  f"{'OVERLAP' if overlap else 'DISJOINT (heterogeneous)'}")

        ais = {k: s["avg_index"] for k, s in subs.items()
               if s["avg_index"] is not None and k in per}
        rank_hit = False
        if len(ais) == len(per) and len(per) >= 3:
            order_ai = sorted(ais, key=ais.get)
            agree = []
            for i in range(3):
                order_r = sorted(per, key=lambda k, ii=i: per[k][ii][0])
                agree.append(order_r == order_ai or
                             order_r == order_ai[::-1])
            rank_hit = all(agree)
            print(f"    avg_index rank {order_ai} ; ratio ranks agree on "
                  f"{sum(agree)}/3 channels -> "
                  f"{'REGIME TREND (heterogeneous)' if rank_hit else 'no trend'}")
        else:
            print(f"    rank test not evaluable: avg_index available for "
                  f"{len(ais)} of {len(per)} subjects")

        het = het_any or rank_hit
        print(f"\n  --> pooling for {arm} is "
              f"{'ILLEGITIMATE (sec.6 step 3)' if het else 'LEGITIMATE (sec.6 step 4)'}")

        # -------------------------------- sec.6 step 4, subjects AND tiles
        print(f"  pooled, unweighted median of per-subject medians"
              f"{' -- DESCRIPTIVE ONLY, not a headline' if het else ''}")
        ks = list(per)
        for i in range(3):
            meds = np.array([per[k][i][0] for k in ks])
            draws = np.empty(nboot)
            for b in range(nboot):
                sk = rng.integers(0, len(ks), len(ks))
                vv = []
                for si in sk:
                    num, den = per[ks[si]][i][3], per[ks[si]][i][4]
                    r = num[den > 0] / den[den > 0]
                    ti = rng.integers(0, len(r), len(r))
                    vv.append(np.median(r[ti]))
                draws[b] = np.median(vv)
            print(f"    {CHAN[i]:11s} {np.median(meds):7.3f} "
                  f"[{np.percentile(draws, 2.5):6.3f},"
                  f"{np.percentile(draws, 97.5):6.3f}]")

        # ------------------------------------------------ sec.7 chroma gate
        if arm == "enfuse":
            bad = [k for k in ks if per[k][1][1] <= 1.0 or per[k][2][1] <= 1.0]
            print(f"\n  sec.7 gate: subjects reading LEVEL or NOISIER on chroma "
                  f"(CI touches 1.0): {bad if bad else 'none'}")
            if len(bad) >= 2:
                print("  --> 'strehl is cleaner than enfuse' is FALSIFIED as a "
                      "general claim; narrow it to the subjects it holds on.")
            else:
                print("  --> sec.7's chroma falsification condition is NOT met.")

    out = {"nboot": nboot,
           "avg_index": {k: s["avg_index"] for k, s in subs.items()},
           "missing": missing}
    with open(os.path.join(ROOT, "pool.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, default=float)
    print(f"\n  written {os.path.join(ROOT, 'pool.json')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
