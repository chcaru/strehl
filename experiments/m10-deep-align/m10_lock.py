"""Control P6 - does the estimator shrink a small scale change by itself?

Reports the recovered/true scale ratio as a function of the planted scale
magnitude, for two arms:

* `field`    - both frames are point samples of the same continuous band-limited
               field.  No interpolator, no resampling, no defocus difference.
               Any shrinkage here is the estimator's own.
* `resample` - the same warps planted by bilinearly resampling a real frame.
               Present only to show the size of the trap that SYNTHESIS section
               5 item 11 records.

Run:  python m10_lock.py
"""

import csv
import sys

import numpy as np

MAGS = [-1.0e-4, -2.0e-4, -4.0e-4, -8.0e-4, -1.6e-3, -3.2e-3, -6.4e-3,
        -1.28e-2, -2.56e-2, -5.12e-2]
LEVER = 1200.0


def load(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if not r["g"]:
                rows.append(dict(arm=r["arm"], cfg=r["cfg"], g_true=float(r["g_true"]),
                                 ok=False, ratio=float("nan"), used=0, rms=float("nan")))
                continue
            rows.append(dict(arm=r["arm"], cfg=r["cfg"], g_true=float(r["g_true"]),
                             ok=True, ratio=float(r["ratio"]), used=int(r["used"]),
                             rms=float(r["rms"])))
    return rows


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else "data/lock-lock.csv"
    rows = load(path)
    print("=" * 78)
    print("P6  PLANTED SMALL-SCALE RECOVERY - resampler-free vs resampled")
    print("  ratio = recovered scale / planted scale.  1.000 is unbiased;")
    print("  below 1 is shrinkage toward zero.  'diff disp' is the differential")
    print("  displacement the planted scale produces across the anchor grid.")
    print("=" * 78)
    for arm in ("field", "resample"):
        for cfg in sorted({r["cfg"] for r in rows}):
            sub = [r for r in rows if r["arm"] == arm and r["cfg"] == cfg]
            if not sub:
                continue
            print(f"\n  arm={arm}  cfg={cfg}")
            print(f"    {'g_true':>10} {'diff disp px':>13} {'n':>4} {'fail':>5} "
                  f"{'ratio':>8} {'p25':>8} {'p75':>8} {'med_used':>9}")
            for g in MAGS:
                es = [r for r in sub if abs(r["g_true"] - g) < 1e-6 * max(abs(g), 1e-6)]
                ok = [r for r in es if r["ok"]]
                if not ok:
                    print(f"    {g:>10.5f} {abs(g) * LEVER:>13.3f} {len(es):>4} "
                          f"{len(es):>5}" + "        -" * 4)
                    continue
                rr = np.array([r["ratio"] for r in ok])
                print(
                    f"    {g:>10.5f} {abs(g) * LEVER:>13.3f} {len(es):>4} "
                    f"{len(es) - len(ok):>5} {np.median(rr):>8.3f} "
                    f"{np.percentile(rr, 25):>8.3f} {np.percentile(rr, 75):>8.3f} "
                    f"{np.median([r['used'] for r in ok]):>9.0f}"
                )
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
