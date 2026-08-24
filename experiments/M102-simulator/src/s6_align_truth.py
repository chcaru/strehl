"""M102 S6 -- score the shipped aligner against a KNOWN warp.

The corpus has measured the aligner's drift, its held-out residual and its
cycle-consistency floor, but all of those are internal: they compare the
aligner to itself. This scores it against a warp that was PLANTED, so the
error is an error and not a disagreement.

The planted warp is the measured breathing model: a radial scale track whose
endpoints come from fact 1177's 232.7 px over fact 1254's 4226 px
half-diagonal. Nothing is fitted here -- the truth is the number the
generator used.

Usage:
  python src/s6_align_truth.py <stackdir> <measured_corner_drift_plane_px>
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m102lib as M  # noqa: E402


def main():
    d = sys.argv[1]
    measured = float(sys.argv[2])
    meta = json.load(open(os.path.join(d, "truth.json")))
    wm = os.path.join(d, "warpmap.txt")
    txt = open(wm).read() if os.path.exists(wm) else ""
    m = re.search(r"plane (\d+)x(\d+)", txt)
    pw, ph = (int(m.group(1)), int(m.group(2))) if m else (
        meta["w"] // 2, meta["h"] // 2)

    s0, s1 = meta["scale_first_last"]
    # Corner radius on the plane grid, centre at ((n-1)/2).
    r = ((pw - 1) ** 2 / 4.0 + (ph - 1) ** 2 / 4.0) ** 0.5
    planted = r * (s1 - s0)

    res = {
        "stack": os.path.basename(d), "frames": meta["frames"],
        "plane": [pw, ph], "corner_radius_plane_px": r,
        "scale_first_last": [s0, s1],
        "planted_corner_drift_plane_px": planted,
        "measured_corner_drift_plane_px": measured,
        "recovery_ratio": measured / planted,
        "shortfall_plane_px": planted - measured,
        "source_facts": {"drift_px": M.DRIFT_PX, "half_diag_px":
                         M.HALF_DIAG_PX, "facts": "1177, 1254"},
    }
    with open(os.path.join(M.OUT, "s6_align_truth.json"), "w") as fh:
        json.dump(res, fh, indent=2)
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
