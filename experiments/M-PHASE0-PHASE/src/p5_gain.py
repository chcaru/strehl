"""Does averaging many measurements beat the per-edge cycle floor?

`p4_floor.py` measured the raw pairwise measurements' self-consistency at
within-DOF spans: 0.27 to 1.43 sensor px, against a bar of 0.10 to 0.12. There is
exactly one way C1 escapes that gap, and it must be tested rather than assumed:

  a global solve does not use one measurement per pose, it uses many, so if the
  per-edge errors are independent the solved pose can be more accurate than any
  edge that fed it, by roughly the square root of the number of constraints.

The gap is 2.7x to 14.2x. An averaging gain of sqrt(k) with k in 10..100 is 3x to
10x. So this objection is live and load-bearing, and it decides KILL versus
NARROWED. It is not answerable by argument -- systematic error does not average
and scene-driven registration error is shared across every edge touching a frame,
so the gain could equally be 1. It has to be measured.

Measured directly from the data, with no solver in the loop:

  for each measured short-span edge (i,k), enumerate every two-hop path
  i -> j -> k that is also measured. Each path predicts (i,k). Compare the
  corner error of a SINGLE path's prediction against the corner error of the
  MEAN of all paths' predictions. The ratio is the realised averaging gain.

The null control alone would be worthless here. A gain of 1.0 is exactly what a
broken instrument reports, so the positive control is the load-bearing one: after
adding iid noise to every edge, the measured gain must rise to about sqrt(n_paths).
An instrument that cannot see planted averaging cannot be believed when it
reports none.

Output: out/p5_gain.json
"""

import json
import os
import sys
from collections import defaultdict

import numpy as np

import flib

EDGES = os.path.join(os.path.dirname(__file__), "..", "out", "edges-dense")
OUT = os.path.join(os.path.dirname(__file__), "..", "out", "p5_gain.json")
MAX_SPAN = 8
MIN_PATHS = 3


def paths_for(edges, i, k):
    """Every measured two-hop path i -> j -> k."""
    out = []
    for j in range(i + 1, k):
        a, b = edges.get((i, j)), edges.get((j, k))
        if a is not None and b is not None:
            out.append(flib.then(a, b))
    return out


def gain_for(edges, plane, max_span=MAX_SPAN, min_paths=MIN_PATHS):
    """Per-edge single-path and mean-path prediction error, in plane px."""
    single, mean, npath = [], [], []
    for (i, k), meas in edges.items():
        if k - i > max_span or k - i < 2:
            continue
        ps = paths_for(edges, i, k)
        if len(ps) < min_paths:
            continue
        errs = [flib.corner_err(p, meas, plane) for p in ps]
        ma = (np.mean([p[0] for p in ps]), np.mean([p[1] for p in ps]))
        single.append(float(np.median(errs)))
        mean.append(flib.corner_err(ma, meas, plane))
        npath.append(len(ps))
    return (np.array(single), np.array(mean), np.array(npath))


def controls():
    print("=" * 78)
    print("p5 commissioning: can this instrument see averaging at all?")
    print("=" * 78)
    ok = [0, 0]

    def chk(name, cond, note):
        ok[0 if cond else 1] += 1
        print("  %-8s %-42s %s" % ("PASS" if cond else "FAIL", name, note))

    plane = (879.0, 586.0)
    rng = np.random.default_rng(7)
    e, _ = flib.synth_consistent(14, rng, plane)

    s, m, n = gain_for(e, plane)
    chk("C-G null: consistent set, no error to average",
        len(s) > 0 and s.max() < 1e-9 and m.max() < 1e-9,
        "%d edges, single %.2e mean %.2e plane px" % (len(s), s.max(), m.max()))

    # Positive control.  iid noise on every edge is the textbook case in which
    # averaging MUST work; if the instrument cannot see the gain here it cannot
    # be trusted to report its absence on real data.
    noisy = {}
    for k_, v in e.items():
        noisy[k_] = (v[0] + rng.normal(0, 2e-4) + 1j * rng.normal(0, 2e-4),
                     v[1] + rng.normal(0, .2) + 1j * rng.normal(0, .2))
    s2, m2, n2 = gain_for(noisy, plane)
    g = float(np.median(s2) / np.median(m2))
    exp = float(np.sqrt(np.median(n2)))
    chk("C-G positive: planted iid noise must average",
        1.3 < g < 2.0 * exp,
        "gain %.2fx over %d paths, sqrt(paths) = %.2fx" % (g, int(np.median(n2)), exp))

    # A gain much above sqrt(k) would mean the metric is inflating the single-path
    # error rather than the mean genuinely improving.
    chk("C-G positive: gain does not exceed sqrt(k) much",
        g < 2.0 * exp, "%.2fx vs %.2fx" % (g, exp))

    # Systematic control: one shared error on every edge cannot be averaged away.
    shifted = {k_: (v[0], v[1] + 0.5) for k_, v in e.items()}
    s3, m3, _ = gain_for(shifted, plane)
    g3 = float(np.median(s3) / np.median(m3))
    chk("C-G systematic: shared error does not average",
        0.9 < g3 < 1.1, "gain %.3fx (must be 1)" % g3)

    print("-" * 78)
    print("  controls PASS %d / FAIL %d" % tuple(ok))
    return ok[1] == 0


def main():
    if not controls():
        print("\nVERDICT: RED -- not measuring real data")
        return 1

    print("\n" + "=" * 78)
    print("realised averaging gain on the census stacks, span 2..%d" % MAX_SPAN)
    print("=" * 78)
    print("  %-15s %6s %10s %10s %8s %8s" %
          ("stack", "edges", "single", "meaned", "gain", "sqrt(k)"))
    res = {}
    for f in sorted(os.listdir(EDGES)):
        if not f.endswith(".csv"):
            continue
        p = os.path.join(EDGES, f)
        edges, plane = flib.load_edges(p), flib.plane_of(p)
        s, m, n = gain_for(edges, plane)
        if len(s) < 3:
            print("  %-15s %6d   (too few multi-path short edges)" % (f[:-4], len(s)))
            continue
        g = float(np.median(s) / np.median(m))
        sk = float(np.sqrt(np.median(n)))
        res[f[:-4]] = dict(n_edges=int(len(s)), single=float(np.median(s)),
                           meaned=float(np.median(m)), gain=g, sqrt_k=sk,
                           median_paths=float(np.median(n)),
                           single_sensor=float(flib.to_sensor(np.median(s))),
                           meaned_sensor=float(flib.to_sensor(np.median(m))))
        print("  %-15s %6d %10.4f %10.4f %8.2fx %8.2fx"
              % (f[:-4], len(s), flib.to_sensor(np.median(s)),
                 flib.to_sensor(np.median(m)), g, sk))

    if res:
        gs = [v["gain"] for v in res.values()]
        print("\n  median realised gain over stacks: %.2fx" % np.median(gs))
        print("  median gain the noise model would predict: %.2fx"
              % np.median([v["sqrt_k"] for v in res.values()]))
        print("  best meaned accuracy any stack reaches: %.4f sensor px"
              % min(v["meaned_sensor"] for v in res.values()))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(dict(stacks=res, max_span=MAX_SPAN, min_paths=MIN_PATHS), f, indent=1)
    print("\nwrote %s" % os.path.normpath(OUT))
    return 0


if __name__ == "__main__":
    sys.exit(main())

