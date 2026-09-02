"""The bar's ceiling: how loose can the requirement get for the best geometry?

`p4_floor.py` and `p5_gain.py` between them fix what is achievable: 0.225 sensor
px on the best census stack, after averaging, and averaging buys only 1.07x
because the error is systematic rather than iid.

That number only decides C1 once the LOOSEST bar is known. The bar is roughly
0.36/kappa, and kappa is a condition number, so kappa >= 1 and the bar has a
finite ceiling. If that ceiling is above 0.225 sensor px, well-conditioned sites
on the best stacks survive and the verdict is NARROWED, and the census has to say
how many such sites exist. If it is below, nothing survives anywhere and the
census cannot change that.

So this reads the 7680 rows of `out/p1_bar.json` and reports the bar in the
best-conditioned bin, per rho and per gauge, rather than at the kappa ~ 3 working
point the headline used.

Nothing here is a new measurement. It is a re-cut of the registered one, and it
is separated out precisely so the re-cut cannot be mistaken for fresh evidence.
"""

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(__file__)
BAR = os.path.join(HERE, "..", "out", "p1_bar.json")
GAIN = os.path.join(HERE, "..", "out", "p5_gain.json")
FLOOR = os.path.join(HERE, "..", "out", "p4_floor.json")


def main():
    d = json.load(open(BAR))
    rows = [r for r in d["rows"] if r["bar_unit"] is not None]
    k = np.array([r["kappa"] for r in rows])

    print("=" * 78)
    print("sanity: kappa is a condition number, so it must be >= 1")
    print("=" * 78)
    print("  min kappa over %d rows: %.6f   %s" %
          (len(k), k.min(), "OK" if k.min() >= 1.0 - 1e-9 else "VIOLATED"))
    if k.min() < 1.0 - 1e-9:
        print("  the 0.36/kappa ceiling argument does not hold; stop here")
        return 1

    print("\n" + "=" * 78)
    print("the bar in the best-conditioned decile, SENSOR px")
    print("(kappa near 1 is the loosest the requirement can ever be)")
    print("=" * 78)
    print("  %-8s %-6s %8s %10s %10s %10s" %
          ("target", "gauge", "rho", "kappa", "bar", "kappa*bar"))
    ceiling = {}
    for tgt in sorted(set(r["target"] for r in rows)):
        for gauge in sorted(set(r["gauge"] for r in rows)):
            for rho in sorted(set(r["rho"] for r in rows)):
                sel = [r for r in rows if r["target"] == tgt and r["gauge"] == gauge
                       and r["rho"] == rho]
                if len(sel) < 10:
                    continue
                ks = np.array([r["kappa"] for r in sel])
                cut = np.percentile(ks, 10)
                best = [r for r in sel if r["kappa"] <= cut]
                b = float(np.median([r["bar_unit"] for r in best]))
                kk = float(np.median([r["kappa"] for r in best]))
                ceiling.setdefault(tgt, {}).setdefault(gauge, {})[rho] = b
                print("  %-8s %-6s %8.3g %10.3f %10.4f %10.3f"
                      % (tgt, gauge, rho, kk, b, kk * b))

    # The single loosest bar anywhere in the registered sweep.
    loosest = max((r["bar_unit"], r) for r in rows)
    print("\n  loosest single bar in the whole sweep: %.4f sensor px"
          % loosest[0])
    print("    at target %s gauge %s rho %g kappa %.3f N %d snr %s"
          % (loosest[1]["target"], loosest[1]["gauge"], loosest[1]["rho"],
             loosest[1]["kappa"], loosest[1]["N"], loosest[1]["snr"]))

    print("\n" + "=" * 78)
    print("VERDICT INPUT: loosest bar vs best achievable")
    print("=" * 78)
    g = json.load(open(GAIN))["stacks"]
    best_ach = min(v["meaned_sensor"] for v in g.values())
    best_stack = min(g, key=lambda s: g[s]["meaned_sensor"])
    print("  best achievable, any census stack, span<=8, after averaging:")
    print("    %.4f sensor px  (%s)" % (best_ach, best_stack))

    for tgt in ceiling:
        for gauge in ceiling[tgt]:
            c = max(ceiling[tgt][gauge].values())
            verdict = ("some sites may survive" if c > best_ach
                       else "no site survives at any conditioning")
            print("  %-8s %-10s loosest decile bar %.4f -> %s (%.2fx)"
                  % (tgt, gauge, c, verdict, best_ach / c))
    return 0


if __name__ == "__main__":
    sys.exit(main())
