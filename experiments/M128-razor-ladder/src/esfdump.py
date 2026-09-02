"""M128 / esfdump -- print the ESF and MTF behind a registration mode.

The four-way registration test returned a 10-90% rise of ~138 um where the
registered prediction is ~12 um, and `amp` pinned at its 0.5 lower bound in
every mode. Those are not biases to be modelled, they say the thing being fitted
is not an edge response. Diagnosing that from summary statistics is guesswork,
so this prints the arrays themselves.
"""

import argparse
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "M88-optical-ceiling" / "src"))
import m88lib as L  # noqa: E402
import geom  # noqa: E402
import sfr_run  # noqa: E402
import esfreg  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("frame")
    ap.add_argument("--which", default="G1")
    ap.add_argument("--row0", type=int, required=True)
    ap.add_argument("--col0", type=int, required=True)
    ap.add_argument("--nrow", type=int, default=120)
    ap.add_argument("--ncol", type=int, default=800)
    ap.add_argument("--half", type=float, default=96.0)
    ap.add_argument("--bin-um", type=float, default=0.64)
    ap.add_argument("--taper", type=float, default=0.10)
    ap.add_argument("--core-um", type=float, default=48.0)
    ap.add_argument("--mode", default="cross")
    ap.add_argument("--every", type=int, default=8)
    ap.add_argument("--dark-first", action="store_true")
    args = ap.parse_args()
    bright_first = not args.dark_first

    active = L.load_active(args.frame)
    sub, xs, ys = L.green_sites(active, args.which)
    oth, _oxs, oys = L.green_sites(active, "G2" if args.which == "G1" else "G1")

    s = sub[args.row0:args.row0 + args.nrow, args.col0:args.col0 + args.ncol]
    xr = xs[args.col0:args.col0 + args.ncol]
    yr = ys[args.row0:args.row0 + args.nrow]
    line = sfr_run.line_from_crossings(s, xr, yr, bright_first, "horizontal")
    x_idx, y_sen, hi, lo = esfreg.locus_sensor_y(s, yr, bright_first)
    so = oth[args.row0:args.row0 + args.nrow, args.col0:args.col0 + args.ncol]
    ox, oy, _h, _l = esfreg.locus_sensor_y(so, oys[args.row0:args.row0 + args.nrow],
                                           bright_first)

    print(f"ROI rows {args.row0}..{args.row0 + args.nrow} "
          f"({args.nrow} sublattice rows = {args.nrow * 2 * L.PITCH_UM:.0f} um tall)")
    print(f"line angle {line['angle_deg']:+.4f}  resid {line['resid_sd_px']:.3f} "
          f"sensor px  hi {line['hi_dn']:.0f} lo {line['lo_dn']:.0f} DN")

    print("\nRAW COLUMN PROFILE at three columns, sublattice row vs DN "
          "(the edge should be a step):")
    for c in (0, args.ncol // 2, args.ncol - 1):
        prof = s[:, c]
        pk = " ".join(f"{v:5.0f}" for v in prof[::max(1, args.nrow // 24)])
        print(f"  col {c:4d}: {pk}")

    print("\nFULL-RESOLUTION PROFILE around the crossing, one column, "
          "sublattice row : DN  (10.24 um per row):")
    c = args.ncol // 2
    j = int(np.argmin(np.abs(x_idx - c))) if len(x_idx) else 0
    ctr = int(round((y_sen[j] - yr[0]) / 2.0)) if len(x_idx) else args.nrow // 2
    for i in range(max(0, ctr - 22), min(args.nrow, ctr + 12)):
        mark = " <== 50% crossing" if i == ctr else ""
        um = (i - ctr) * 2.0 * L.PITCH_UM
        print(f"  row {i:4d} ({um:+7.1f} um): {s[i, c]:6.0f}{mark}")

    fit, r = esfreg.run_mode(sub, xs, ys, args.row0, args.col0, args.nrow,
                             args.ncol, args.mode, line, x_idx, y_sen, (ox, oy),
                             args.half, args.bin_um, args.taper, args.core_um,
                             10.0, 150.0, "drop", bright_first)
    cc, ee, raw, cnt = (r["centres_um"], r["esf"], r["esf_raw"], r["count"])
    print(f"\nmode {args.mode}: fc {fit['fc_cymm']:.2f} sigma {fit['sigma_um']:.3f} "
          f"amp {fit['amp']:.4f} rms {fit['rms_resid']:.5f}")
    print(f"deramp slopes L {r['slope_l']:+.4f} R {r['slope_r']:+.4f} DN/um  "
          f"esf contrast {r['contrast']:.1f} DN")
    print(f"\nESF ({len(cc)} bins over {cc[0]:+.1f}..{cc[-1]:+.1f} um), "
          f"every {args.every}th bin:")
    print(f"  {'um':>8} {'esf raw':>10} {'esf deramp':>11} {'count':>6}")
    for i in range(0, len(cc), args.every):
        print(f"  {cc[i]:8.2f} {raw[i]:10.1f} {ee[i]:11.1f} {cnt[i]:6.0f}")

    f, m = r["freq_cymm"], r["mtf"]
    print(f"\nMTF ({len(f)} points), through 200 cy/mm:")
    print(f"  {'cy/mm':>8} {'mtf':>9}")
    sel = f <= 200.0
    fs, ms = f[sel], m[sel]
    step = max(1, len(fs) // 24)
    for i in range(0, len(fs), step):
        bar = "#" * max(0, int(round(40 * min(max(ms[i], 0.0), 1.2))))
        print(f"  {fs[i]:8.2f} {ms[i]:9.4f} {bar}")


if __name__ == "__main__":
    main()
