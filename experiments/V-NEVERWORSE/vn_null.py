r"""V-NEVERWORSE / THE NULL -- what does a ratio of 1.85x mean if a typical
SOURCE FRAME also reads above 1 against the same denominator?

`vs_min` compares one number (the master) against the MINIMUM of N numbers
(the sources). That is not a fair fight and it is not supposed to be -- the
invariant literally asks for the best frame. But it means `vs_min > 1` is the
DEFAULT outcome for any member of the source distribution, not evidence of
anything, and rule 39 forbids reporting a ratio without its null.

So: leave-one-out. For each admissible source frame f, hold it out and score it
exactly the way the master is scored -- `stat(f) / min(stat(g) for g != f)`.
That gives N observations of "one draw from this subject's frames, against the
best of the rest", which is the master's own question asked of a frame that is
definitionally NOT a merge. The comparison is then:

    excess = vs_min(master) / median(loo)

`excess > 1` says the merge is worse than a typical frame would be at the same
game. `excess <= 1` says the reading is the denominator's shape, not the merge.

Two more things this file computes, both free once the rows are loaded:

  RANK.  `beaten` = how many admissible frames strictly beat the master. This
  is extremum-free: if the master were an ordinary draw from the same
  distribution its rank would be uniform, so P(every frame beats it) = 1/(n+1).
  A one-sided exact sign test on that is reported. Rank cannot be argued away
  as a bias of the min.

  DETAIL.  `relhf` (3 px energy / mean) for the master against the source
  median at the SAME window. This is the documented innocent explanation for
  blotch > 1: a merge that resolves 50-400 px structure the individual frames
  blur will read more band energy for a good reason. NOTE THE BOUND: W1 showed
  the source warp suppresses relhf to 0.71x-0.82x, and the master is not
  warped, so master/source relhf is BIASED UP by roughly that factor. The
  conservative reading is `relhf_ratio * 0.82`, which is also printed.

  python vn_null.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vn_lib as L                                            # noqa: E402

RDIR = os.path.join(L.OUT, "ratio")
WARP_SUPPRESSION = 0.82     # W1, worst-case relhf retention under source warp


def loo(vals):
    """Each value scored against the best of the OTHERS, as the master is."""
    out = []
    for i, v in enumerate(vals):
        rest = [x for j, x in enumerate(vals) if j != i]
        if not rest:
            continue
        m = min(rest)
        if m <= 0:
            continue
        out.append(v / m)
    return out


def sign_p(beaten, n):
    """One-sided exact P(rank at least this bad) under 'master is an ordinary
    draw'. Ranks are uniform over the n+1 interleavings, so P(at least `beaten`
    frames beat it) = (n + 1 - beaten) / (n + 1)."""
    if n <= 0:
        return None
    return (n + 1 - beaten) / float(n + 1)


def main():
    subs = L.subjects()
    print("V-NEVERWORSE / NULL -- leave-one-out, rank, and the detail defence")
    print("loo = median over source frames of stat(f)/min(stat(other frames))")
    print("excess = vs_min(master) / loo_med ; >1 means the MERGE, not the min\n")
    hdr = ("%-36s %8s %8s %8s %7s | %6s %6s %8s | %7s %7s"
           % ("subject", "vs_min", "loo_med", "loo_max", "excess",
              "beat", "n", "p", "relhf", "x0.82"))
    print("BLOTCH");  print(hdr)
    res = {}
    for key in ("blotch", "chroma"):
        if key == "chroma":
            print("\nCHROMA"); print(hdr)
        for s in subs:
            p = os.path.join(RDIR, "%s.json" % s)
            if not os.path.exists(p):
                continue
            rec = L.jload(p)
            ok = [r for r in rec["rows"]
                  if L.admits(r, key) and r.get(key) is not None]
            if len(ok) < 7:
                continue
            vals = [r[key] for r in ok]
            m = rec["master"][key]
            lo = loo(vals)
            if not lo:
                continue
            lm, lx = float(np.median(lo)), float(max(lo))
            vs = m / min(vals)
            beaten = sum(1 for v in vals if v < m)
            pv = sign_p(beaten, len(vals))
            rh = (rec["master"]["relhf"]
                  / max(float(np.median([r["relhf"] for r in ok])), 1e-12))
            res.setdefault(s, {})[key] = dict(
                vs_min=vs, loo_med=lm, loo_max=lx, excess=vs / lm,
                beaten=beaten, n=len(vals), p=pv, relhf_ratio=rh)
            print("%-36s %8.4f %8.4f %8.4f %7.3f | %3d/%-3d %6d %8.4f | %7.3f %7.3f"
                  % (s, vs, lm, lx, vs / lm, beaten, len(vals), len(vals), pv,
                     rh, rh * WARP_SUPPRESSION))

    print("\nSUMMARY")
    for key in ("blotch", "chroma"):
        rows = [(s, d[key]) for s, d in res.items() if key in d]
        if not rows:
            continue
        ex = [d["excess"] for _, d in rows]
        above = [(s, d["excess"]) for s, d in rows if d["excess"] > 1.0]
        allbeat = [(s, d["n"]) for s, d in rows if d["beaten"] == d["n"]]
        print("  %-7s vs_min > 1 on %d/%d ; but EXCESS OVER THE NULL > 1 on %d/%d"
              % (key, sum(1 for _, d in rows if d["vs_min"] > 1), len(rows),
                 len(above), len(rows)))
        print("          excess median %.3f  range %.3f..%.3f"
              % (float(np.median(ex)), min(ex), max(ex)))
        print("          EVERY admissible frame beats the master on %d/%d subjects: %s"
              % (len(allbeat), len(rows),
                 ", ".join("%s(n=%d)" % t for t in sorted(allbeat)) or "none"))
    L.jdump(res, os.path.join(L.OUT, "report", "null.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
