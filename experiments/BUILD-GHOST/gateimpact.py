"""PART 2, the number that actually decides it: does the gate get mis-weighted?

Part 2 measures flux drift across a whole bracket, and magtest.py shows that
where the drift is large it is mostly MAGNIFICATION (focus breathing spreads
the same photons over m^2 more pixels), not gain.

That distinction does NOT make the problem go away, and it is important not to
report it as though it does.  Warping a frame back to the reference geometry
resamples it: interpolation moves intensity values around, it does not restore
photons that magnification diluted.  So the flux deficit SURVIVES alignment,
and the merge's noise gate sees a photometric mismatch whether the cause was
the aperture or the focus ring.  Mechanism and impact are different questions.

But the bracket TOTAL is the wrong statistic for impact.  The merge does not
average frame 1 against frame 299; at any given output pixel it combines the
frames that are in focus THERE, which is a narrow window of adjacent frames.
The mismatch that matters is the flux spread WITHIN that window.

Rather than guess the window, this reports the spread as a function of window
width W, so a reader can read off whatever W the merge actually uses.  W = n
is the worst case (the whole bracket).

MEASURED, not argued: every number here comes from the per-frame camera-linear
flux series already written by exposure.py.

USAGE
    python experiments/BUILD-GHOST/gateimpact.py
"""
from __future__ import annotations

import json
import os

import numpy as np

DATA = os.path.join(r"C:\dev\strehl-out\BUILD-GHOST", "data")
WINDOWS = (2, 4, 8, 16, 32)

# A photometric mismatch below this is not worth a code change: it is smaller
# than the shot-noise-driven weight variation the gate already tolerates.
# Stated, not fitted; the full W-dependence is printed so it can be recomputed.
MATTERS_STOPS = 0.05


def main() -> int:
    sweep = json.load(open(os.path.join(DATA, "sweep.json")))
    names = [r["subject"] for r in sweep["subjects"]]

    print("=" * 104)
    print("PART 2 IMPACT  flux spread among frames that co-contribute to one output pixel")
    print("=" * 104)
    print("peak-to-peak camera-linear flux spread, in stops, over a sliding window of W frames")
    print("(worst window in the bracket; W=n is the whole-bracket figure Part 2 reports)\n")
    print(f"{'subject':38s} {'n':>4s} " +
          " ".join(f"{'W=' + str(w):>7s}" for w in WINDOWS) + f" {'W=n':>7s}  matters@W")

    rows = {}
    n_matter = {w: 0 for w in WINDOWS}
    for name in names:
        fp = os.path.join(DATA, f"exposure_{name}.json")
        if not os.path.exists(fp):
            continue
        expo = json.load(open(fp))
        s = np.array([f["stops"] for f in expo["per_frame"]], dtype=float)
        n = len(s)
        vals = []
        for w in WINDOWS:
            if n < w:
                vals.append(float("nan"))
                continue
            # worst peak-to-peak over any contiguous window of w frames
            worst = max(float(s[i:i + w].max() - s[i:i + w].min())
                        for i in range(n - w + 1))
            vals.append(worst)
        total = float(s.max() - s.min())
        first_bad = next((f"W>={w}" for w, v in zip(WINDOWS, vals)
                          if v == v and v >= MATTERS_STOPS), "never")
        for w, v in zip(WINDOWS, vals):
            if v == v and v >= MATTERS_STOPS:
                n_matter[w] += 1
        rows[name] = {"n": n, "by_w": dict(zip(map(str, WINDOWS), vals)),
                      "total": total, "first_bad": first_bad}
        print(f"{name:38s} {n:4d} " +
              " ".join(f"{v:7.4f}" if v == v else "    ---" for v in vals) +
              f" {total:7.4f}  {first_bad}")

    print(f"\nsubjects examined {len(rows)}")
    print(f"threshold: a mismatch matters at >= {MATTERS_STOPS:g} stops")
    for w in WINDOWS:
        print(f"  at W={w:<3d} subjects exceeding it: {n_matter[w]:2d} / {len(rows)}"
              f"   (below: {len(rows) - n_matter[w]:2d})")
    worst_total = sum(1 for r in rows.values() if r["total"] >= MATTERS_STOPS)
    print(f"  at W=n   subjects exceeding it: {worst_total:2d} / {len(rows)}"
          f"   (below: {len(rows) - worst_total:2d})")

    json.dump({"windows": list(WINDOWS), "matters_stops": MATTERS_STOPS,
               "n_matter_by_w": {str(k): v for k, v in n_matter.items()},
               "n_matter_whole_bracket": worst_total,
               "n_subjects": len(rows), "rows": rows},
              open(os.path.join(DATA, "gateimpact.json"), "w"), indent=2, default=float)
    print(f"\nwrote {os.path.join(DATA, 'gateimpact.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
