"""Does the *synthetic* stack reproduce the scale-rate ladder?

`m10_conserve.py` measured, on the real coffee-bean stack, that telescoping
span-1 edges gives -1.69% total magnification change while span-16 to span-64
edges give -5.2 to -5.9%. Every row measures the same physical quantity, so the
spread is bias.

The P4 synthetic stack has a **known** answer, a genuine growing defocus ramp,
and the same estimator. Running the same telescoping identity on it separates
two possibilities that the real data cannot:

* if the synthetic ladder is **flat**, the ramp is not produced by the pipeline,
  the tiling, the fit or defocus-in-general, and the real ramp is a property of
  the real capture;
* if the synthetic ladder **ramps**, the effect is reproducible in a controlled
  setting and the planted truth pins down which end of the ladder is wrong.

The planted per-frame magnification rate is printed alongside, because the
mechanism controls P6/P7 locate the bias at sub-pixel *differential
displacement*, and differential displacement is that rate times the lever arm.
"""

import csv
import sys

import numpy as np

from m10_lib import read_edges


def read_truth(path):
    g = {}
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            g[int(r["frame"])] = (1.0 + float(r["g"])) + 1j * float(r["rot"])
    return [g[k] for k in sorted(g)]


def main(argv):
    case = argv[1] if len(argv) > 1 else "p4-warp"
    n = int(argv[2]) if len(argv) > 2 else 105
    truth = read_truth(f"data/{case}-truth.csv")
    rows = [e for e in read_edges(f"data/{case}-edges.csv", cfg="m10") if e.ok]
    emap = {(e.i, e.j): e for e in rows}
    lever = float(np.median([e.lever for e in rows]))

    true_tot = float(np.log(abs(truth[n - 1]) / abs(truth[0])))
    print("=" * 84)
    print(f"CONSERVATION TEST ON THE SYNTHETIC STACK - {case}")
    print("  Same telescoping identity as m10_conserve.py, but the answer")
    print("  is known.  A flat ladder means the pipeline does not create one.")
    print("=" * 84)
    print(f"\n  planted total   : {100 * (np.exp(true_tot) - 1):+.4f}%")
    print(f"  median lever arm: {lever:.0f} plane px")
    print(f"\n  {'span':>5} {'links':>6} {'covered':>9} {'total %':>10} "
          f"{'ratio to truth':>15} {'planted diff disp px':>21}")
    for s in [1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64]:
        tot, links, cov = 0.0, 0, 0
        k = 0
        while k + s < n:
            e = emap.get((k, k + s))
            if e is not None:
                tot += float(np.log(abs(e.a)))
                links += 1
                cov += s
            k += s
        if links == 0:
            continue
        # planted differential displacement for a single edge of this span,
        # averaged over the stack: |a_true(i,i+s) - 1| * lever
        dd = []
        for i in range(0, n - s):
            r = abs(truth[i + s]) / abs(truth[i])
            dd.append(abs(r - 1.0) * lever)
        print(f"  {s:>5} {links:>6} {cov:>4}/{n - 1:<4} "
              f"{100 * (np.exp(tot) - 1):>10.4f} {tot / true_tot:>15.4f} "
              f"{np.median(dd):>21.3f}")

    print("\n  For comparison, the real coffee-bean ladder (out/conservation.txt):")
    print("    span  1 -> -1.6876%   span 16 -> -5.8891%   span 64 -> -5.2877%")
    print("    i.e. a factor 3.33 between the ends.")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
