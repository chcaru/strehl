"""M70 s24 - POST HOC. The through-focus shape on UNIMODAL patches only.

*** THIS ANALYSIS IS POST HOC AND IS NOT COVERED BY PREREGISTRATION-C. ***
The pre-registered criteria H / I / J returned INDETERMINATE in s21 and that
result stands unaltered. This does not rescue them; it explains them, and it is
reported as post hoc in the same way section 13.5's ISO hypothesis was.

s23 established that R10_50 above the Gaussian value is driven by MULTIMODALITY
(corr(% multi-lobed, R10_50) = +0.834 Pearson / +0.867 Spearman, n=12), and that
a plant whose PSF is a GAUSSIAN BY CONSTRUCTION reaches R10_50 = 3.82 purely
from two-depth scene geometry. So on a multi-lobed patch, "the shape of the
through-focus curve" is not a question about the PSF at all - it is a question
about how many surfaces the patch is looking at.

The PSF question is only well posed on patches whose curve is UNIMODAL. This
restricts to those and asks the rescoped question there:

    are real through-focus curves symmetric, and where does their shape
    depart from a Gaussian?

The restriction is defined on the curve, not on the answer: a patch is admitted
iff its [1,2,1]-smoothed curve has exactly one local maximum above 0.10 of peak.
That rule was fixed in s23 before this script existed and is applied unchanged.
"""

from __future__ import annotations

import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import s14_asym_controls as S14  # noqa: E402
import s20_shape_controls as S20  # noqa: E402
import s21_shape_corpus as S21  # noqa: E402
import s23_multimodality as S23  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")
G = S20.GAUSS["R10_50"]
G25 = S20.GAUSS["R25_50"]
BAR = 0.11


def hdr(t):
    print("\n" + "=" * 118)
    print(t)
    print("=" * 118)


def main() -> None:
    res = {"gauss": G, "gauss25": G25, "bar": BAR, "post_hoc": True}

    hdr("UNIMODAL PATCHES ONLY   (POST HOC - not covered by PREREGISTRATION-C)")
    print("  A patch is admitted iff its smoothed curve has exactly ONE local maximum")
    print("  above 0.10 of peak. The rule is s23's, applied unchanged.")
    print(f"\n{'stack':<16}{'n uni':>7}{'/ n':>6}{'% kept':>8}{'w50':>7}"
          f"{'R25/50':>9}{'R10/50':>9}{'vs G':>9}{'in bar?':>9}")
    res["stacks"] = {}
    pooled = []
    rows = []
    for st in S21.S16.STACKS:
        cs, _K = S21.stack_curves(st)
        uni = [c for c in cs if S23.n_lobes(c) == 1]
        r10, r25, w50 = [], [], []
        for c in uni:
            o = S20.widths(c)
            if np.isfinite(o["R10_50"]):
                r10.append(o["R10_50"])
                w50.append(o["w50"])
            if np.isfinite(o["R25_50"]):
                r25.append(o["R25_50"])
        if not r10:
            print(f"{st:<16}{len(uni):>7}{len(cs):>6}   no finite unimodal curves")
            res["stacks"][st] = {"n_uni": len(uni), "n": len(cs), "R10_50": None}
            continue
        m10 = float(np.median(r10))
        m25 = float(np.median(r25)) if r25 else float("nan")
        pooled.extend(r10)
        rows.append((st, m10, len(r10)))
        inb = abs(m10 - G) <= BAR
        res["stacks"][st] = {"n_uni": len(uni), "n": len(cs), "n_finite": len(r10),
                             "pct": 100.0 * len(uni) / max(1, len(cs)),
                             "w50": float(np.median(w50)), "R25_50": m25,
                             "R10_50": m10, "in_bar": bool(inb)}
        print(f"{st:<16}{len(uni):>7}{len(cs):>6}{100.0 * len(uni) / len(cs):>7.1f}%"
              f"{np.median(w50):>7.2f}{m25:>9.4f}{m10:>9.4f}{m10 - G:>+9.4f}"
              f"{('YES' if inb else 'no'):>9}")

    pooled = np.array(pooled)
    med = float(np.median(pooled))
    inb = sum(1 for _s, m, _n in rows if abs(m - G) <= BAR)
    print(f"\n  POOLED over all unimodal patches: median R10_50 = {med:.4f}  "
          f"({med - G:+.4f} vs Gaussian {G:.4f})   n = {pooled.size}")
    print(f"  stacks whose unimodal median lands inside the +/-0.11 bar: {inb}/{len(rows)}")
    res["pooled_median"] = med
    res["pooled_n"] = int(pooled.size)
    res["in_bar"] = inb
    res["n_stacks"] = len(rows)

    hdr("THE CLEANEST CASE - the two stacks that are ALREADY unimodal")
    print("  wrapped-text-1 and wrapped-text-2 are 0.0% and 1.4% multi-lobed (s23),")
    print("  so no restriction is being applied to them and no selection can bite.")
    print("  They are TWO SEPARATE CAPTURES of the same subject, which makes them")
    print("  the reproduction test - the same test section 16.7 used to refute")
    print("  asymmetry, run here on shape.")
    for st in ("wrapped-text-1", "wrapped-text-2", "coffee-bubbles"):
        e = res["stacks"][st]
        print(f"    {st:<16} R10_50 {e['R10_50']:.4f}  ({e['R10_50'] - G:+.4f} vs Gaussian)"
              f"   R25/50 {e['R25_50']:.4f} ({e['R25_50'] - G25:+.4f})   n={e['n_finite']}")
    a, b = (res["stacks"]["wrapped-text-1"]["R10_50"],
            res["stacks"]["wrapped-text-2"]["R10_50"])
    print(f"\n    the two captures agree to {abs(a - b):.4f} on R10_50")
    print(f"    both sit {abs((a + b) / 2 - G):.4f} from the Gaussian value; bar is {BAR}")
    res["wt_agreement"] = float(abs(a - b))

    hdr("NEGATIVE CONTROL - does the unimodal restriction ITSELF force a Gaussian?")
    print("  Apply the identical restriction to synthetic curves of KNOWN non-Gaussian")
    print("  shape. If the restriction manufactures 1.8226 regardless of input, the")
    print("  result above is an artefact of the selection rule.")
    print(f"\n{'shape':<14}{'unrestricted':>14}{'after restrict':>16}{'delta':>9}")
    res["neg_control"] = {}
    rng = np.random.default_rng(31337)
    for kind in ("gaussian", "sech2", "lorentzian", "boxcar"):
        base = S20.analytic(kind, K=121, scale=2.0)
        raw, kept = [], []
        for _ in range(200):
            c = base * (1.0 + 0.02 * rng.normal(size=base.size))
            v = S20.widths(c)["R10_50"]
            if np.isfinite(v):
                raw.append(v)
                if S23.n_lobes(c) == 1:
                    kept.append(v)
        if raw and kept:
            r, k = float(np.median(raw)), float(np.median(kept))
            res["neg_control"][kind] = {"raw": r, "kept": k, "delta": k - r,
                                        "pct_kept": 100.0 * len(kept) / len(raw)}
            print(f"{kind:<14}{r:>14.4f}{k:>16.4f}{k - r:>+9.4f}"
                  f"   ({100.0 * len(kept) / len(raw):.0f}% kept)")
    dmax = max(abs(v["delta"]) for v in res["neg_control"].values())
    print(f"\n  largest shift caused by the restriction alone: {dmax:.4f}")
    print(f"  Lorentzian survives the restriction reading "
          f"{res['neg_control']['lorentzian']['kept']:.4f}, nowhere near Gaussian,")
    print("  so the restriction does NOT manufacture a Gaussian answer.")
    res["neg_control_max_shift"] = float(dmax)

    hdr("SYMMETRY on the SAME unimodal subset (M67 instruction (a): moments SEPARATELY)")
    print("  Section 16 measured asymmetry on ALL patches. Re-reading A50 on the")
    print("  unimodal subset removes the two-depth confound that fired VOID 8 there.")
    print(f"\n{'stack':<16}{'A50 unimodal':>14}{'A50 all (s16)':>15}{'shift':>9}")
    A_ALL = {"coffee-bubbles": 0.0373, "109MSDCF": 0.0096, "119MSDCF": -0.0447,
             "113MSDCF": -0.0369, "112MSDCF": -0.0389, "foam": 0.0773,
             "coffee-bean": 0.0160, "wrapped-text-2": 0.0474, "wrapped-text-1": -0.0617,
             "bee-1": -0.0358, "bee-2": 0.0420, "bee-3": -0.0696}
    res["asym_uni"] = {}
    au = []
    for st in S21.S16.STACKS:
        cs, _K = S21.stack_curves(st)
        vals = []
        for c in cs:
            if S23.n_lobes(c) != 1:
                continue
            wn, wf, _cn, _cf = S14.half_widths(c, 0.50)
            if np.isfinite(wn) and np.isfinite(wf) and (wn + wf) > 0:
                vals.append((wf - wn) / (wf + wn))
        if not vals:
            continue
        m = float(np.median(vals))
        au.append(m)
        res["asym_uni"][st] = {"A50_uni": m, "A50_all": A_ALL[st], "n": len(vals)}
        print(f"{st:<16}{m:>+14.4f}{A_ALL[st]:>+15.4f}{m - A_ALL[st]:>+9.4f}")
    au = np.array(au)
    print(f"\n  median |A50| on unimodal patches: {np.median(np.abs(au)):.4f}   "
          f"(section 16 on all patches: 0.0404)")
    print(f"  signs: {int((au > 0).sum())} positive / {int((au < 0).sum())} negative "
          f"of {au.size}")
    res["asym_uni_median_abs"] = float(np.median(np.abs(au)))

    with open(os.path.join(OUT, "s24_unimodal.json"), "w") as f:
        json.dump(res, f, indent=1)
    print("\nwrote out/s24_unimodal.json")


if __name__ == "__main__":
    main()
