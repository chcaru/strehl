#!/usr/bin/env python3
"""Digest the stage-1 focus JSONs into the capture-side evidence, per subject.

Nothing here touches a merge.  These are statements about what the CAPTURE
contains, derived only from frames compared against other frames.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tri  # noqa: E402


def digest(sub: str) -> dict:
    with open(os.path.join(tri.OUT, "focus", sub + ".json"), encoding="utf-8") as fh:
        f = json.load(fh)
    bl = f["blocks"]
    ns = len(f["sampled"])

    # A block is "live" if its best frame holds real structure; a block with no
    # structure in ANY frame has nothing to be sharp about and must not be
    # allowed to vote on a coverage gap.
    hf = np.array([b["hf_max_dn"] for b in bl])
    live = hf > max(2.0, 0.10 * float(hf.max()))

    # COVERAGE GAP.  A covered region's focus response rises to an interior
    # peak and falls away on BOTH sides.  A region whose response is still
    # climbing when the bracket runs out was never brought into focus, and the
    # end it is climbing towards is the end that needs more frames.
    gap_near = [b for b, l in zip(bl, live)
                if l and b["argmax_sample"] <= 1 and b["fall_near"] < 0.25]
    gap_far = [b for b, l in zip(bl, live)
               if l and b["argmax_sample"] >= ns - 2 and b["fall_far"] < 0.25]

    m = f.get("motion", {})
    steps = np.array(m.get("per_step_px_rawG", [0.0]))
    med = float(np.median(steps)) if steps.size else 0.0
    # Drift walks steadily; motion jumps.  The ratio of the worst step to the
    # typical step separates them without needing an absolute threshold.
    jump = float(steps.max() / med) if med > 0.05 else float(steps.max())

    return {
        "subject": sub,
        "n_frames": f["n_frames"],
        "sampled": ns,
        "blocks": len(bl),
        "live_blocks": int(live.sum()),
        "src_hf_max_dn": round(float(hf.max()), 3),
        "src_hf_med_dn": round(float(np.median(hf[live])) if live.any() else 0.0, 3),
        "gap_near": [(b["r"], b["c"]) for b in gap_near],
        "gap_far": [(b["r"], b["c"]) for b in gap_far],
        "n_gap": len(gap_near) + len(gap_far),
        "motion_path_px": m.get("path_px_rawG"),
        "motion_net_px": m.get("total_px_rawG"),
        "motion_max_step_px": m.get("max_step_px_rawG"),
        "motion_med_step_px": round(med, 3),
        "motion_jumpiness": round(jump, 2),
    }


def main() -> int:
    subs = sys.argv[1:] or tri.SUBJECTS
    rows = [digest(s) for s in subs]
    print(f"{'SUBJECT':<38s} {'N':>4s} {'live':>5s} {'srcHF':>8s} {'gapN':>5s} "
          f"{'gapF':>5s} {'path':>7s} {'net':>7s} {'maxstp':>7s} {'jump':>6s}")
    for r in rows:
        print(f"{r['subject']:<38s} {r['n_frames']:>4d} "
              f"{r['live_blocks']:>2d}/{r['blocks']:<2d} {r['src_hf_max_dn']:>8.2f} "
              f"{len(r['gap_near']):>5d} {len(r['gap_far']):>5d} "
              f"{r['motion_path_px'] or 0:>7.1f} {r['motion_net_px'] or 0:>7.1f} "
              f"{r['motion_max_step_px'] or 0:>7.2f} {r['motion_jumpiness']:>6.1f}")
    with open(os.path.join(tri.OUT, "capture.json"), "w", encoding="utf-8") as fh:
        json.dump(rows, fh, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
