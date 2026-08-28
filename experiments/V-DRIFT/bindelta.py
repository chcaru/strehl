#!/usr/bin/env python3
"""How far apart are the pin and HEAD renders, in the statistics this lane used?

`binsame.py` proves the bytes differ.  A byte difference is not yet a finding:
one LSB of dither and a changed election look identical at that resolution and
have completely different consequences for V-SELECT.  This script measures the
size of the difference in the quantities the conclusions actually rest on:

  mean confidence          the level statistic behind section 5
  fraction hedged >500     the shape statistic behind sections 5-7
  per-pixel image delta    whether the delivered image moved at all
  low-band amplitude       the detail statistic behind sections 11.3-11.4

If the confidence statistics have moved by less than the effects claimed, the
conclusions survive the binary change and only their provenance needs restating.
If they have moved by more, the ladders must be re-run and this lane must say so.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "BUILD-TRIAGE"))
import tri  # noqa: E402

ROOT = Path(r"C:\dev\strehl-out\V-DRIFT")
SCRATCH = ROOT / "binsame"
CASES = [("flower", 12, 18), ("flower", 2, 103), ("bee", 12, 25)]
KS = {18: 0.9973, 103: 0.9972, 25: 0.9217}


def conf_stats(p: Path) -> tuple[float, float]:
    a = tri.load16(str(p)).astype(np.float64)
    a = a[..., 0] if a.ndim == 3 else a
    return float(a.mean()), float((a > 500).mean() * 100.0)


def main() -> int:
    rows = []
    print(f"{'case':22s} {'mean pin':>9s} {'mean head':>10s} {'delta':>8s} "
          f"{'>500 pin':>9s} {'>500 head':>10s} {'img rms':>9s} {'lowA pin':>9s} "
          f"{'lowA head':>10s}")
    print("-" * 104)
    for subject, stride, n in CASES:
        tag = f"{subject}-s{stride}-n{n}"
        ma, fa = conf_stats(SCRATCH / f"{tag}-pin-conf.tif")
        mb, fb = conf_stats(SCRATCH / f"{tag}-head-conf.tif")
        A = tri.luma(tri.load16(str(SCRATCH / f"{tag}-pin.tif")))
        B = tri.luma(tri.load16(str(SCRATCH / f"{tag}-head.tif")))
        h, w = min(A.shape[0], B.shape[0]), min(A.shape[1], B.shape[1])
        A, B = A[:h, :w], B[:h, :w]
        rms = float(np.sqrt(((A - B) ** 2).mean()))
        y, x = (h - 512) // 2, (w - 512) // 2
        k = KS[n]
        la = tri.band_amp(A[y:y + 512, x:x + 512], k)["low"]
        lb = tri.band_amp(B[y:y + 512, x:x + 512], k)["low"]
        rows.append({"case": tag, "mean_pin": ma, "mean_head": mb,
                     "d_mean": mb - ma, "frac_pin": fa, "frac_head": fb,
                     "img_rms_dn": rms, "lowA_pin": la, "lowA_head": lb})
        print(f"{tag:22s} {ma:9.1f} {mb:10.1f} {mb - ma:+8.1f} {fa:8.2f}% "
              f"{fb:9.2f}% {rms:9.1f} {la:9.1f} {lb:10.1f}")

    (ROOT / "bindelta.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    print("\nReference scales this must be judged against:")
    print("  section 6 knob span, hard-max -> exponent 0.5 : 120.3 confidence units")
    print("  section 7 whole-field depth effect            : 6.6 / 11.0 units")
    print("  section 12 flat-quartile headroom             : 71.2 - 97.3 units")
    print("  16-bit LSB on a 65535 scale                   : 1.0 DN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
