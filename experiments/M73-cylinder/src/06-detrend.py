"""M73 step 06 — how much work the per-column LINE fit is doing.

Section 2.3 of the pre-registration chose to remove a per-column line in `y`
rather than a constant, to buy immunity from axis-angle error, taper and
rotation. That choice was registered before any winner map was scored. This file
measures what it bought, by scoring the same residual both ways.

If the linear term is small, the choice was a nicety. If it is large, a
constant-fit version of this test would have been swamped by geometry and the
transferred prediction would have been measured through a large common-mode
term that compresses the E-over-A ratio toward 1.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "out"

spec = importlib.util.spec_from_file_location("score03", ROOT / "src" / "03-score.py")
s3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s3)


def main() -> int:
    out: dict = {}
    for tag, stack in (("s1", "wrapped-text-1"), ("s2", "wrapped-text-2")):
        d = s3.load(OUT / tag)
        h, w = d["height"], d["width"]
        rows = np.arange(s3.MARGIN, h - s3.MARGIN)
        cols = np.arange(s3.MARGIN, w - s3.MARGIN)
        sub = np.ix_(rows, cols)
        ve, va = d["win_E"][sub], d["win_A"][sub]

        line = s3.column_line_fit(d["win_E"][:, cols], rows)
        const = np.broadcast_to(d["win_E"][sub].mean(axis=0), ve.shape)

        b = (line[-1] - line[0]) / (rows[-1] - rows[0])
        swing = b * (rows[-1] - rows[0])
        print(f"\n{'=' * 78}\n{stack}\n{'=' * 78}")
        print(f"column slope b(x) : median {np.median(b):+.4e} frames/px   "
              f"p05 {np.percentile(b, 5):+.4e}   p95 {np.percentile(b, 95):+.4e}")
        print(f"end-to-end swing  : median {np.median(swing):+.3f} frames over "
              f"{rows[-1] - rows[0]} rows   p95 |swing| {np.percentile(np.abs(swing), 95):.3f}")

        res = {}
        for nm, ref in (("line", line), ("const", const)):
            se = float(np.abs(ve - ref).mean())
            sa = float(np.abs(va - ref).mean())
            res[nm] = {"S_E": se, "S_A": sa, "ratio": se / sa}
            print(f"  fit = {nm:<5}      : S(E) {se:.5f}  S(A) {sa:.5f}  ratio {se / sa:.5f}")
        infl = res["const"]["S_E"] / res["line"]["S_E"]
        print(f"  constant-fit inflation of S(E) : {infl:.3f}x")
        print(f"  ratio moves {res['line']['ratio']:.5f} -> {res['const']['ratio']:.5f}  "
              f"(toward 1.000 by {res['const']['ratio'] - res['line']['ratio']:+.5f})")
        out[stack] = {
            "slope_median": float(np.median(b)),
            "slope_p05": float(np.percentile(b, 5)),
            "slope_p95": float(np.percentile(b, 95)),
            "swing_median_frames": float(np.median(swing)),
            "swing_p95_abs_frames": float(np.percentile(np.abs(swing), 95)),
            "rows_spanned": int(rows[-1] - rows[0]),
            **res,
            "const_inflation": infl,
        }
    (OUT / "06-detrend.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("\nwrote", OUT / "06-detrend.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
