"""M70 s16 - per-stack null band for the symmetry statistic.

s15's frame-shuffle placebo compared point estimates. That is not enough to say
whether a stack's reading is distinguishable from a destroyed curve. This builds
the null DISTRIBUTION of the median statistic, per stack, by repeated shuffling,
and asks how many stacks fall outside their own null.

Reported because s15 showed the two shortest stacks (K=19, K=22) returned a
LARGER apparent asymmetry under shuffling than intact - i.e. at the sparse end of
the step-density range the statistic may have no power at all.
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import m70lib as M  # noqa: E402
import s05_analyse as A5  # noqa: E402
import s07_unclipped as S7  # noqa: E402
import s15_asym_corpus as S15  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")
STACKS = list(S7.APERTURE.keys())
REPS = 100
SEED = 70
KEYS = ("A50", "A25", "A10", "g1")


def curves(stack: str):
    d = A5.load(stack)
    s, nvar = A5.signal(d, 1.0)
    tex, _ = A5.classify(d, s, nvar)
    out = []
    for p in np.where(tex)[0]:
        for bname in M.MID_BANDS:
            out.append(s[:, p, d["bands"].index(bname)].astype(np.float64))
    return out, s.shape[0]


def med_stat(cs, key):
    v = np.array([S15.stats_with_cens(c)[key] for c in cs], dtype=np.float64)
    v = v[np.isfinite(v)]
    return float(np.median(v)) if v.size else float("nan")


def main() -> None:
    rng = np.random.default_rng(SEED)
    res = {}
    print("=" * 118)
    print(f"SHUFFLE NULL BAND for the stack-median statistic, {REPS} reps per stack")
    print("A stack is DISTINGUISHABLE when its intact median falls outside the")
    print("central 95% of its own shuffled null. This is a per-stack power check.")
    print("=" * 118)
    print(f"{'stack':<16}{'K':>5}{'n':>5}" + "".join(
        f"{k + ' obs':>10}{k + ' null95':>18}{'out':>5}" for k in ("A50", "g1")))

    for st in STACKS:
        cs, K = curves(st)
        e = {"K": K, "n": len(cs)}
        for key in KEYS:
            obs = med_stat(cs, key)
            null = []
            for _ in range(REPS):
                null.append(med_stat([rng.permutation(c) for c in cs], key))
            null = np.array(null, dtype=np.float64)
            null = null[np.isfinite(null)]
            lo, hi = float(np.percentile(null, 2.5)), float(np.percentile(null, 97.5))
            e[key] = {
                "obs": obs,
                "null_lo": lo,
                "null_hi": hi,
                "null_sd": float(null.std(ddof=1)),
                "outside": bool(obs < lo or obs > hi),
            }
        res[st] = e
        line = f"{st:<16}{K:>5}{len(cs):>5}"
        for key in ("A50", "g1"):
            q = e[key]
            line += (f"{q['obs']:>+10.4f}   [{q['null_lo']:>+6.4f},"
                     f"{q['null_hi']:>+6.4f}]{'YES' if q['outside'] else ' no':>5}")
        print(line)

    print("\n" + "=" * 118)
    print("SUMMARY - stacks whose intact median is outside its own shuffled null")
    print("=" * 118)
    for key in KEYS:
        n = sum(1 for st in STACKS if res[st][key]["outside"])
        who = [st for st in STACKS if res[st][key]["outside"]]
        print(f"  {key}: {n}/12   {', '.join(who) if who else '(none)'}")
    print("\n  null sd of the stack-median, by stack (the per-stack noise floor):")
    print(f"{'stack':<16}{'K':>5}" + "".join(f"{k:>10}" for k in KEYS))
    for st in STACKS:
        print(f"{st:<16}{res[st]['K']:>5}" +
              "".join(f"{res[st][k]['null_sd']:>10.4f}" for k in KEYS))

    ks = np.array([res[st]["K"] for st in STACKS], dtype=np.float64)
    sd = np.array([res[st]["A50"]["null_sd"] for st in STACKS])
    print(f"\n  corr(log K, null sd of median A50) = "
          f"{np.corrcoef(np.log(ks), sd)[0, 1]:+.3f}")
    print("  A rising null sd at low K means the sparse end of the step-density")
    print("  range has less power, not more symmetry.")

    with open(os.path.join(OUT, "s16_null_band.json"), "w") as f:
        json.dump(res, f, indent=1)
    print("\nwrote out/s16_null_band.json")


if __name__ == "__main__":
    main()
