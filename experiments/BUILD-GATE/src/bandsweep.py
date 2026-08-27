"""Driver: cache the bracket once, score every gate arm on both constructions.

The expensive part is developing the raws (~8.7 s/frame, rawpy dominant). It is
done ONCE per subject and every arm is then scored from the cache, which also
guarantees the arms are compared against a numerically identical reference --
the property that makes the arm-to-arm deltas immune to selection inflation.

Sites are picked ONCE, on the reference master, and reused for every arm. If
each arm re-picked its own sites the arms would be scored on different pixels
and the comparison would be meaningless.
"""
import os
import sys

import numpy as np
import tifffile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bandceiling as bc                                          # noqa: E402
from orch_sharp1to1 import CROP, luma                             # noqa: E402

SWEEP = r"C:\dev\strehl-out\BUILD-GATE\sweep"
ARMS = ["WHITE200", "G100", "G140", "G170", "G200", "G300", "G400"]
CACHE = r"C:\dev\strehl-out\BUILD-GATE\bandcache"


def cache_path(subject):
    return os.path.join(CACHE, subject + ".npz")


def do_build(subject, ref_arm="WHITE200"):
    os.makedirs(CACHE, exist_ok=True)
    ref = os.path.join(SWEEP, ref_arm, subject + ".tiff")
    d = bc.build(subject, ref)
    np.savez_compressed(cache_path(subject), **d)
    print("cached %s: %d frames, hi_fraction=%.4f"
          % (subject, d["nframes"], d["hi_fraction"]), flush=True)


def do_score(subject):
    z = np.load(cache_path(subject), allow_pickle=True)
    sites, cache = z["sites"], z["cache"]
    rows = {}
    for arm in ARMS:
        p = os.path.join(SWEEP, arm, subject + ".tiff")
        if not os.path.exists(p):
            continue
        my = luma(tifffile.imread(p)[..., :3].astype(np.float64))
        per = []
        for si, (y, x) in enumerate(sites):
            mb = bc.tile_bands(my[y:y + CROP, x:x + CROP])
            per.append(bc.ratios(mb, cache[si]))
        rows[arm] = {k: float(np.mean([q[k] for q in per])) for k in ("max", "disj")}
    return rows, float(z["hi_fraction"])


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "build":
        for s in sys.argv[2:]:
            do_build(s)
    elif cmd == "score":
        print("%-16s %-9s %8s %8s %9s %9s"
              % ("subject", "arm", "max", "disj", "d%max", "d%disj"))
        for s in sys.argv[2:]:
            rows, hi = do_score(s)
            base = rows["WHITE200"]
            for arm in ARMS:
                if arm not in rows:
                    continue
                r = rows[arm]
                print("%-16s %-9s %8.4f %8.4f %+9.2f %+9.2f"
                      % (s, arm, r["max"], r["disj"],
                         100 * (r["max"] / base["max"] - 1),
                         100 * (r["disj"] / base["disj"] - 1)))
            print("%-16s hi_fraction(fine above 0.25 cyc/px) = %.4f" % (s, hi))
