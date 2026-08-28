r"""ORCH job 2 continued.

Two things this file exists to do.

1. FIX A DEFECT IN MY OWN SPECIFICITY ARM. vr_ring.cmd_spec built its rim-free
   curve as monotone everywhere plus transplanted noise INSIDE THE RING WINDOW
   ONLY. That left the null window perfectly smooth, so the ratio rule was
   guaranteed to fire and the 24/24 detection rates it printed are worthless.
   The ring amplitudes it printed are still valid -- those do not touch the
   null window -- but the detection rates are withdrawn. Here the transplanted
   fluctuation covers the WHOLE grid, so ring window and null window are
   treated identically and the ratio rule is given a fair test.

2. PROVENANCE CROSS-CHECK against the published mid-scale table. The published
   run read C:\dev\strehl-out\V-RIM\lin, rendered by a binary pinned at commit
   1cacb61; neither survives. The published table does carry one number per
   subject that does not depend on the ring at all -- the edge depth at t=+1 as
   a percentage of the far field. If that agrees between the vanished render
   and the deliverable, the two images are the same scene measured the same
   way and a 25-80x collapse in ring amplitude is a property of the render or
   of the estimator, not of my having pointed it somewhere else.
"""
import io
import json
import os
import sys

import numpy as np

from vr_ring import load, FIVE, OTHER, SCRATCH
from ringstat import ring_and_null, RING_LO, RING_HI

# transcribed from experiments/V-RIM/logs/summarise.log, the published run
PUBLISHED = {
    "bee-1-cpl":                           (-21.90, +0.97, 119, 1.77),
    "bee-2-cpl":                           (-31.77, +5.06, 127, 3.65),
    "bee-3-cpl":                           (-35.36, +4.48,  29, 0.77),
    "flower-bud-alone-cpl":                (-35.20, +3.18,  22, 0.00),
    "flower-bud-with-background-fern-cpl": (-32.54, +9.76,  21, 0.08),
    "lavendar-cpl":                        (-25.13, +2.93,  22, 0.18),
    "109MSDCF":                            (-35.32, +1.36,  49, 40.20),
    "119MSDCF":                            (-37.07, +0.56, 125, 0.57),
    "coffee-bean":                         (-38.78, +7.13,  34, 0.59),
}


def spec2(labels, ntrial=48):
    print("=" * 100)
    print("SPECIFICITY, CORRECTED -- the subject's own far-field fluctuation")
    print("  transplanted over the WHOLE grid on a monotone rise. Ring window and")
    print("  null window get identical treatment. NO RING EXISTS in these curves.")
    print("=" * 100)
    print("%-38s %8s %8s %9s %9s %10s"
          % ("subject", "real%", "fake%", "fakenull%", "det rate", "verdict"))
    rng = np.random.default_rng(20260828)
    rows = []
    for lab in labels:
        d = load(lab)
        if d is None or not d.get("straight"):
            continue
        s = d["straight"]
        grid = np.asarray(s["grid"], float)
        med = np.asarray(s["med"], float)
        far = float(s["far"])
        r0, n0 = ring_and_null(grid, med, far)
        fm = (grid >= 150) & (grid <= 300)
        x = grid[fm]
        A = np.vstack([x, np.ones_like(x)]).T
        resid = med[fm] - A @ np.linalg.lstsq(A, med[fm], rcond=None)[0]
        mono = np.maximum.accumulate(med)
        hits, fr, fn = 0, [], []
        for k in range(ntrial):
            reps = int(np.ceil(grid.size / resid.size)) + 1
            pool = np.concatenate([rng.permutation(resid) for _ in range(reps)])
            fake = mono + pool[:grid.size]
            rf, nf = ring_and_null(grid, fake, far)
            fr.append(rf["frac"]); fn.append(nf["frac"])
            if rf["frac"] >= 3 * max(nf["frac"], 0.0005):
                hits += 1
        fr, fn = np.array(fr), np.array(fn)
        v = ("rim-free reads >= real" if fr.mean() >= r0["frac"]
             else "real above rim-free")
        print("%-38s %+7.2f%% %+7.2f%% %8.2f%% %8s %10s"
              % (lab, 100 * r0["frac"], 100 * fr.mean(), 100 * fn.mean(),
                 "%d/%d" % (hits, ntrial), v))
        rows.append(dict(subject=lab, real=r0["frac"], fake=float(fr.mean()),
                         fakenull=float(fn.mean()), hits=hits, n=ntrial))
    return rows


def provenance(labels):
    print()
    print("=" * 100)
    print("PROVENANCE -- deliverable vs the published run on the vanished 1cacb61 render")
    print("=" * 100)
    print("%-38s %19s %19s %14s"
          % ("subject", "edge %far  pub/new", "ring %  pub/new", "t_peak pub/new"))
    rows = []
    for lab in labels:
        d = load(lab)
        if d is None or not d.get("straight") or lab not in PUBLISHED:
            continue
        pf, pr, pt, pn = PUBLISHED[lab]
        s, a = d["straight"], d["all"]
        r, n = ring_and_null(s["grid"], s["med"], s["far"])
        print("%-38s %9.2f %9.2f %9.2f %9.2f %6.0f %7.0f"
              % (lab, pf, 100 * a["frac1"], pr, 100 * r["frac"], pt,
                 r["t_peak"]))
        rows.append(dict(subject=lab, pub_edge=pf, new_edge=100 * a["frac1"],
                         pub_ring=pr, new_ring=100 * r["frac"],
                         pub_t=pt, new_t=r["t_peak"]))
    e = np.array([abs(x["pub_edge"] - x["new_edge"]) for x in rows])
    g = np.array([x["pub_ring"] / max(x["new_ring"], 1e-6) for x in rows])
    print()
    print("  edge depth: median |pub-new| = %.2f points over %d subjects"
          % (np.median(e), len(rows)))
    print("  ring:       median pub/new   = %.1fx" % np.median(g))
    return rows


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    labs = FIVE + OTHER
    doc = dict(spec2=spec2(labs), provenance=provenance(labs))
    json.dump(doc, io.open(os.path.join(SCRATCH, "ring2.json"), "w",
                           encoding="utf-8"), indent=1, default=float)
    print("\nwrote ring2.json")
