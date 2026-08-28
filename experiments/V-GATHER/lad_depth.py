r"""Is the excess that SURVIVES at exponent 1 real, or is it my own ceiling?

THE OBSERVATION THAT PROMPTS THIS. Seven of nine subjects fall to zero or below
at exponent 1. Two do not: flower-inner-edge-cpl keeps +28.8% of a +69.4%
shipping excess and pencil-steep-angle-cpl keeps +43.6% of +96.4%. Those two are
also the only two 299-frame stacks in the set. That coincidence has to be
resolved before the residual is reported as merge behaviour.

THE COMPETING EXPLANATION, AND IT IS AN ARTIFACT OF MY OWN INSTRUMENT. The
ceiling is a MAX over a SAMPLE of frames, and sharpaxis.py caps the search at 56
renders. On a 19-frame stack every frame is seen and the ceiling is the true
ceiling. On a 299-frame stack at most 56 of 299 are seen, so the sampled max
sits BELOW the true max and the excess measured against it is OVERSTATED. That
bias is not a criticism of the ladder -- it is frozen across arms and cannot
create a trend -- but it lands directly on the absolute value at exponent 1,
which is the one number being read as "how much excess is not explained by the
selection law".

WHAT WOULD DISTINGUISH THEM. If the residual is a sampling artifact it should
track HOW COMPLETELY THE CEILING WAS SAMPLED, not the exponent. This measures
that coverage from sharp.json -- frames rendered over frames available -- and
ranks it against the residual. A rank correlation near -1 says the residual is
my ceiling; near 0 says the two are unrelated and the residual is the merge's.

NOTHING HERE RENDERS. It reads records already written, so it is safe to run
while the per-site pass holds the binary.
"""
import io
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lad_measure as lm                                           # noqa: E402


def load(n):
    p = os.path.join(HERE, n)
    return json.load(io.open(p, encoding="utf-8")) if os.path.exists(p) else {}


def spearman(x, y):
    def rank(v):
        o = np.argsort(np.argsort(np.asarray(v, dtype=float)))
        return o.astype(float)
    rx, ry = rank(x), rank(y)
    rx -= rx.mean()
    ry -= ry.mean()
    d = float(rx.std() * ry.std())
    return float(np.mean(rx * ry) / d) if d > 1e-30 else float("nan")


def main():
    lad = load("ladder.json")
    sharp = {}
    for f in ("sharp.json", "sharp2.json"):
        for k, v in load(f).items():
            sharp.setdefault(k, v)

    print("=== ceiling search coverage vs the excess left at exponent 1 ===")
    print("  %-24s %6s %6s %8s %10s %10s %10s"
          % ("subject", "n_raw", "used", "coverage", "e1", "shipping", "residual"))
    cov, res, rows = [], [], []
    for sub, e in lad.items():
        s = sharp.get(sub)
        a = e.get("arms", {})
        e1 = a.get("e1", {}).get("median")
        d = a.get("default", {}).get("median")
        if not s or not lm.finite(e1, d):
            print("  %-24s incomplete" % sub)
            continue
        nr, nu = s.get("n_raw"), s.get("n_frames_used")
        if not nr or not nu:
            print("  %-24s no frame counts in sharp.json" % sub)
            continue
        c = float(nu) / float(nr)
        frac = e1 / d if abs(d) > 1e-9 else float("nan")
        print("  %-24s %6d %6d %7.1f%% %+9.3f%% %+9.3f%% %9s"
              % (sub, nr, nu, 100 * c, 100 * e1, 100 * d,
                 ("%.1f%%" % (100 * frac)) if np.isfinite(frac) else "  n/a"))
        cov.append(c)
        res.append(e1)
        rows.append((sub, nr, c, e1, d))

    print("\n=== rank correlation ===")
    print("  Spearman(ceiling coverage, excess at e1)      : %+.4f  (n=%d)"
          % (spearman(cov, res), len(cov)))
    print("  Spearman(n_raw, excess at e1)                 : %+.4f"
          % spearman([r[1] for r in rows], res))
    print("  A residual that is really the merge's should not track either.")

    print("\n=== the same question without a correlation: split by coverage ===")
    full = [r for r in rows if r[2] >= 0.999]
    part = [r for r in rows if r[2] < 0.999]
    for name, grp in (("ceiling FULLY sampled", full), ("ceiling PARTIALLY sampled", part)):
        if not grp:
            print("  %-26s (empty)" % name)
            continue
        v = [r[3] for r in grp]
        print("  %-26s n=%d  excess at e1: median %+8.3f%%  range %+8.3f%% .. %+8.3f%%"
              % (name, len(v), 100 * float(np.median(v)), 100 * min(v), 100 * max(v)))
        print("  %-26s   %s" % ("", ", ".join(r[0] for r in grp)))

    print("\n=== HOW FAR THE CEILING COULD STILL RISE ===")
    print("  For a partially sampled stack the true ceiling is at least the sampled one,")
    print("  so the excess at e1 is an UPPER bound. The gap needed to explain it away:")
    for sub, nr, c, e1, d in rows:
        if c >= 0.999 or e1 <= 0:
            continue
        print("  %-24s ceiling would have to be %.1f%% higher than the %d frames found it"
              % (sub, 100 * e1, int(round(c * nr))))


if __name__ == "__main__":
    main()
