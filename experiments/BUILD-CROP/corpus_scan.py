"""Rank every delivered master by the chroma-fringe signature.

Runs `chromaedge.measure` over a directory of masters and prints a ranked
table, plus the four-way verdict ORCH asked for. The verdict boundaries are
declared here rather than chosen after seeing the ranking:

  UNSCORED  too few edge pixels to measure -- NEVER counted as clean
  VISIBLE   score >= VISIBLE_AT, calibrated against the subject ORCH found by
            eye, so at least one subject is VISIBLE by construction and the
            boundary is anchored to a human observation rather than a quantile
  MEASURED  score >= MEASURED_AT but below VISIBLE_AT: the signature is present
            above the instrument's planted-1px response but was not seen
  CLEAN     below MEASURED_AT

MEASURED_AT is set to the instrument's own planted-1px score, so "clean" means
"carries less fringe than a planted one-pixel displacement", which is a stated
sensitivity rather than an absence of evidence.

Usage:
    python corpus_scan.py <dir-of-masters> [--visible 0.010]
"""

import argparse
import pathlib
import sys

import numpy as np
import tifffile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from chromaedge import measure  # noqa: E402

MEASURED_AT = 0.000884   # the planted 1 px response, measured in commissioning


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--visible", type=float, default=0.010)
    ap.add_argument("--thresh", type=float, default=0.25)
    ap.add_argument("--edgepct", type=float, default=98.0)
    args = ap.parse_args()

    rows = []
    for p in sorted(pathlib.Path(args.dir).glob("*.tiff")):
        img = np.asarray(tifffile.imread(str(p))).astype(np.float32)
        if img.ndim == 2:
            img = np.dstack([img] * 3)
        m = measure(img[:, :, :3], args.thresh, args.edgepct)
        if m["unscored"]:
            verdict = "UNSCORED"
        elif m["score"] >= args.visible:
            verdict = "VISIBLE"
        elif m["score"] >= MEASURED_AT:
            verdict = "MEASURED"
        else:
            verdict = "CLEAN"
        rows.append((m["score"], p.stem, verdict, m))
        print(f"{p.stem:34} {m['score']:10.6f}  edgeMag={100*m['mag_edge']:7.4f}%  "
              f"flatMag={100*m['mag_flat']:7.4f}%  {verdict}", flush=True)

    print("\n=== RANKED ===")
    counts = {"VISIBLE": 0, "MEASURED": 0, "CLEAN": 0, "UNSCORED": 0}
    for score, name, verdict, m in sorted(rows, key=lambda t: -t[0]):
        ratio = (m["mag_edge"] / m["mag_flat"]) if m["mag_flat"] > 0 else float("inf")
        print(f"{name:34} {score:10.6f}  edge/flat={ratio:8.1f}x  {verdict}")
        counts[verdict] += 1
    print(f"\nVISIBLE={counts['VISIBLE']}  MEASURED={counts['MEASURED']}  "
          f"CLEAN={counts['CLEAN']}  UNSCORED={counts['UNSCORED']}  "
          f"TOTAL={sum(counts.values())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
