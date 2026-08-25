"""N7 -- sweep the support floor, and check it is graded rather than saturated.

ORCH's correction #2 makes two points that land on `MIN_AMPLITUDE = 2000 DN`:

  "A support floor is a real defence... if your estimator has a minimum-support
   threshold, it is probably protecting you already... The protection is graded
   -- watch the sample count, not just the result."

  "A control whose sampling saturates has tested nothing, and it will print a
   clean negative... Log the sample count of every control at every level and
   require it to vary."

M121 has such a floor, and it was chosen from `amp_probe.py` before any verdict
was read.  But it was chosen at ONE value and never swept, so two things were
never established:

  1. whether the headline depends on the choice of 2000 DN, and
  2. whether the floor actually excludes anything across its range -- a floor
     that admits everything at every setting is the saturation failure ORCH
     describes, and it would have made N4's clean negative meaningless.

This sweeps it and requires the sample count to move.

Outputs: C:\\dev\\strehl-out\\M121\\n7\\n7-floor.json
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from m121_io import OUT, arm_path, load_u16, luma, sha256  # noqa: E402
from runner import scan  # noqa: E402
import e2_polarity as E2  # noqa: E402

N7 = OUT / "n7"

# 0 is "no floor at all" -- the setting that produced the -0.30 N4 failure.
FLOORS = [0.0, 500.0, 1000.0, 1500.0, 2000.0, 3000.0, 4000.0, 6000.0]

HEADLINE = "dark_object_bright_surround"
NULLROW = "bright_object_dark_surround"


def main():
    N7.mkdir(parents=True, exist_ok=True)
    out: dict = {"floors": [], "shipped_floor": E2.MIN_AMPLITUDE}

    max_rise = E2.commissioned_max_rise()
    p = arm_path("armM4-gate4-binlin")
    print(f"loading {p.name} ...")
    y = luma(load_u16(p))
    out["arm"] = {"path": str(p), "sha256": sha256(p)}

    print("building the object-side classifier ...")
    frames = [luma(load_u16(arm_path(f))) for f in E2.FRAMES]
    fmax = np.max(np.stack([E2.focus_field(f) for f in frames]), axis=0)
    classify = E2.make_classifier(fmax)
    del frames, fmax

    print(f"\n{'floor DN':>10}{'headline':>11}{'n_hl':>7}{'null':>10}"
          f"{'n_null':>8}{'measured':>10}")
    print("-" * 60)

    for floor in FLOORS:
        r = scan(y, label=f"N7 floor={floor:g}", grad_percentile=E2.GRAD_PCT,
                 max_edges=E2.MAX_EDGES, isolation_frac=E2.ISO,
                 flat_tol=E2.FLAT_TOL, classify=classify,
                 min_amplitude=floor, max_rise=max_rise, verbose=False)
        t = E2.polarity_table(r)
        hl = t.get(HEADLINE) if isinstance(t.get(HEADLINE), dict) else None
        nu = t.get(NULLROW) if isinstance(t.get(NULLROW), dict) else None
        rim = hl.get("surround_rim") if hl else None
        nrim = nu.get("surround_rim") if nu else None
        n_hl = hl.get("n") if hl else 0
        n_nu = nu.get("n") if nu else 0
        meas = int(r.get("n_measured") or 0)
        out["floors"].append({
            "floor_dn": floor, "headline_rim": rim, "n_headline": n_hl,
            "null_rim": nrim, "n_null": n_nu, "n_measured": meas,
            "headline_frac_pos": hl.get("frac_positive") if hl else None,
        })
        print(f"{floor:>10.0f}{(rim if rim is not None else float('nan')):>+11.4f}"
              f"{n_hl:>7}{(nrim if nrim is not None else float('nan')):>+10.4f}"
              f"{n_nu:>8}{meas:>10}")

    print("-" * 60)

    ns = [g["n_headline"] for g in out["floors"]]
    varied = len(set(ns)) > 1
    out["sampling_varied"] = varied
    out["n_headline_by_floor"] = ns
    print(f"\nsample count across floors: {ns}")
    if not varied:
        raise SystemExit(
            "N7 HARD ERROR: the floor admitted the same sample at every "
            "setting.  Per ORCH's rule this sweep has tested nothing, and N4's "
            "clean negative cannot be quoted until this is understood."
        )
    print("  the floor genuinely excludes, and does so gradedly.")

    rims = [g["headline_rim"] for g in out["floors"]
            if g["headline_rim"] is not None]
    if rims:
        lo, hi = min(rims), max(rims)
        out["headline_range"] = [lo, hi]
        out["headline_spread_pct"] = 100.0 * (hi - lo) / abs(np.median(rims))
        print(f"  headline over the whole sweep: {lo:+.4f} .. {hi:+.4f} "
              f"(spread {out['headline_spread_pct']:.1f}% of median)")

    with open(N7 / "n7-floor.json", "w") as fh:
        json.dump(out, fh, indent=2, default=float)
    print(f"wrote {N7 / 'n7-floor.json'}")


if __name__ == "__main__":
    main()
