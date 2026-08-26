"""How much did the unnormalised focus metric bias the best-frame pick?

focuscurve.py ranks frames by plain Laplacian RMS in DN.  That quantity scales
with signal level, and 13 of the 26 subjects brighten monotonically through the
bracket -- up to +46.8%.  So the "best frame" can be the BRIGHTEST frame rather
than the sharpest one, and compare.py then measures the merge against a frame
that is not the sharpest the capture offered.  That error flatters the merge,
which is the dangerous direction for a report whose headline is "the merge
loses nothing".

This estimates the size of the bias without re-decoding anything, by dividing
each stored block curve by the recorded per-sample global level trace.  The
illumination drift is global (exposure/lighting, not per-region), so the global
trace is the right first-order correction.  It is an ESTIMATE and is labelled
as one: it decides which subjects deserve a real re-measurement, nothing more.
"""
from __future__ import annotations

import glob
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tri  # noqa: E402


def main() -> int:
    rows = []
    for p in sorted(glob.glob(os.path.join(tri.OUT, "focus", "*.json"))):
        sub = os.path.basename(p)[:-5]
        with open(p, encoding="utf-8") as fh:
            f = json.load(fh)
        lv = np.array(f["level_dn"], np.float64)
        drift = float(lv[-1] / max(lv[0], 1e-9))
        sampled = f["sampled"]
        moved, big, tot = 0, 0, 0
        worst = 0
        for b in f["blocks"]:
            c = np.array(b["curve"], np.float64)
            if c.size != lv.size or c.max() <= 0:
                continue
            tot += 1
            a_raw = int(np.argmax(c))
            a_cor = int(np.argmax(c / lv))
            if a_raw != a_cor:
                moved += 1
                d = abs(sampled[a_raw] - sampled[a_cor])
                worst = max(worst, d)
                if d > 5:
                    big += 1
        rows.append({
            "subject": sub, "drift": drift, "blocks": tot,
            "moved": moved, "moved_gt5": big, "worst_move_frames": worst,
            "moved_pct": 100.0 * moved / max(tot, 1),
        })

    rows.sort(key=lambda r: -r["worst_move_frames"])
    print(f"{'subject':38s} {'drift':>6s} {'moved':>10s} {'>5f':>4s} {'worst':>6s}")
    for r in rows:
        flag = "  <== re-measure" if r["worst_move_frames"] > 5 else ""
        print(f"{r['subject']:38s} {r['drift']:6.3f} "
              f"{r['moved']:4d}/{r['blocks']:<3d}({r['moved_pct']:3.0f}%) "
              f"{r['moved_gt5']:4d} {r['worst_move_frames']:6d}{flag}")

    hit = [r for r in rows if r["worst_move_frames"] > 5]
    print(f"\nsubjects whose best-frame pick moves by more than 5 frames "
          f"under level correction: {len(hit)} of {len(rows)}")
    for r in hit:
        print(f"  {r['subject']}  (drift x{r['drift']:.3f}, "
              f"worst move {r['worst_move_frames']} frames)")

    out = os.path.join(tri.OUT, "levelbias.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({"note": "ESTIMATE via global level trace; picks which "
                           "subjects need real re-measurement", "rows": rows},
                  fh, indent=1)
    print(f"-> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
