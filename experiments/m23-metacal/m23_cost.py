"""M23 cost: what do the two extra correlation evaluations per edge actually cost?

The budget in the milestone brief is "two extra correlation evaluations per
edge".  This measures it rather than asserting it.

Method.  The `metacal` mode does `1 + 2*|deltas|` fits per pair.  Running it
with one delta (3 fits/pair) and with two deltas (5 fits/pair) on the SAME pair
set isolates the marginal cost of one +-delta pair as `(t2 - t1) / 2`, and the
base fit as `t1 - 2*marginal`.  Nothing has to be timed by reading code.

RULE 16.  This is a sweep over |deltas|, so: each setting is run twice, the two
orders are alternated (1,2 then 2,1) to cancel any cache or thermal drift, and
the PER-SETTING MINIMUM is taken.  The result is quoted as a bound on the cost,
not a value.

FAILURE DIRECTION: wall clock fails upward.  A cost that came out lower than
the budget would be the suspicious direction and is checked against the
independently reported ms/fit in the run logs.

Run:  python m23_cost.py > out\\cost.txt
"""

from __future__ import annotations

import re
import subprocess
import time

BIN = r"target\release\m23-metacal.exe"
DIR = r"C:\dev\macro\test\coffee-bean"
PAIRS = 104  # span 1 over 105 frames

RUNS = [
    ("d1", ["0.0002"]),
    ("d2", ["0.0002", "0.0008"]),
    ("d2", ["0.0002", "0.0008"]),
    ("d1", ["0.0002"]),
]


def once(deltas):
    t0 = time.time()
    p = subprocess.run(
        [BIN, "metacal", DIR, "cost-tmp", "--case", "cost", "--cfgs", "m10",
         "--spans", "1", "--deltas", ",".join(deltas)],
        capture_output=True, text=True,
    )
    wall = time.time() - t0
    err = p.stderr
    m = re.search(r"= (\d+) fits in ([\d.]+) s \(([\d.]+) ms/pair, ([\d.]+) ms/fit\)", err)
    dec = re.search(r"in (\d+) ms \(([\d.]+) ms/frame\)", err)
    if not m:
        print(err)
        raise SystemExit("could not parse timing")
    return dict(wall=wall, fits=int(m.group(1)), secs=float(m.group(2)),
                ms_pair=float(m.group(3)), ms_fit=float(m.group(4)),
                decode_ms=int(dec.group(1)) if dec else -1)


def main() -> int:
    print("=" * 92)
    print("COST OF THE METACALIBRATION PROBE - measured, alternated, per-setting minimum")
    print(f"  {PAIRS} span-1 pairs of coffee-bean, cfg=m10, 32 logical cores")
    print("  order run: " + " -> ".join(k for k, _ in RUNS))
    print("=" * 92)
    got: dict[str, list[dict]] = {"d1": [], "d2": []}
    for k, d in RUNS:
        r = once(d)
        got[k].append(r)
        print(f"  {k}: {r['fits']:>4} fits, measure {r['secs']:>6.2f} s "
              f"({r['ms_pair']:>6.1f} ms/pair, {r['ms_fit']:>5.1f} ms/fit), "
              f"decode {r['decode_ms']} ms, wall {r['wall']:.1f} s")

    t1 = min(x["secs"] for x in got["d1"])
    t2 = min(x["secs"] for x in got["d2"])
    per_pair1 = t1 / PAIRS * 1e3
    per_pair2 = t2 / PAIRS * 1e3
    marg = (per_pair2 - per_pair1) / 2.0
    base = per_pair1 - 2.0 * marg

    print("\n  PER-SETTING MINIMUM (rule 16)")
    print(f"    1 delta  (3 fits/pair): {t1:>6.2f} s  -> {per_pair1:>6.1f} ms/pair")
    print(f"    2 deltas (5 fits/pair): {t2:>6.2f} s  -> {per_pair2:>6.1f} ms/pair")
    print(f"\n  DERIVED decomposition")
    print(f"    one +-delta pair (the 'two extra correlation evaluations'): "
          f"<= {2 * marg:>6.1f} ms/edge")
    print(f"    base fit alone (implied):                                   "
          f"~ {base:>6.1f} ms/edge")
    print(f"    cost multiplier for one delta:                              "
          f"<= {per_pair1 / base if base > 0 else float('nan'):>6.2f}x")
    print("    (quoted as a BOUND: the two settings differ by a fixed 2 fits, so the")
    print("     difference is an upper bound on the marginal cost, and the implied")
    print("     base is correspondingly a lower bound.)")

    print("\n  WHAT THIS COSTS AT DEPLOYMENT SCALE (DERIVED)")
    for edges, what in [(207, "coffee-bean spans 1-2"),
                        (1601, "coffee-bean full m10 edge set")]:
        print(f"    {what:<34} {edges:>5} edges x {2 * marg:>5.1f} ms "
              f"= {edges * 2 * marg / 1e3:>7.2f} s of extra probe time")
    print("\n  MEASURED end-to-end for the arms this milestone actually ran:")
    print("    coffee-bean  523 pairs x 5 deltas = 5753 fits in  93.0 s (16.2 ms/fit)")
    print("    112MSDCF     367 pairs x 5 deltas = 4037 fits in  66.7 s (16.5 ms/fit)")
    print("    cb-self       52 pairs x 5 deltas =  572 fits in  10.4 s (18.1 ms/fit)")
    print("    cb-ped        52 pairs x 5 deltas =  572 fits in  10.3 s (18.1 ms/fit)")
    print("    cb-self-ped   52 pairs x 5 deltas =  572 fits in  10.3 s (18.0 ms/fit)")
    print("    field-p0      12 reps                          in 207.7 s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
