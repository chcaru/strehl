"""s06: the measurement.  Runs the pre-registered instrument on real captures.

Frozen settings and ROIs come from PREREGISTRATION.md sections 2.2 and 4.
Nothing here is tunable from the command line except which stack to run and
which green sublattice to use.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import m88lib as L  # noqa: E402

ROOT = Path("D:/personal/macro")
OUT = Path(__file__).resolve().parents[1] / "out"

BIN_UM, HALF_UM, TAPER = 0.64, 192.0, 0.10
F_LO, F_HI = 10.0, 150.0
NB = (250.0, 380.0)
Z, RUN = 3.0, 3
F_FOCUS = 40.0
F_READ = (48.828125, 86.30, 97.65625)

ROIS = {
    "119MSDCF": [("A1", 1280, 0), ("A2", 1280, 200), ("A3", 1280, 400),
                 ("A4", 1280, 600), ("B1", 800, 0)],
    "109MSDCF": [("C1", 1280, 0), ("C2", 1280, 200), ("C3", 1200, 400),
                 ("C4", 1200, 600)],
    "tweezers-cpl": [("D1", 2080, 2000), ("D2", 2080, 2400),
                     ("D3", 2080, 2600)],
}
NROW, NCOL, AXIS = 160, 400, "horizontal"


def measure_roi(sub, xs, ys, row0, col0):
    s = sub[row0:row0 + NROW, col0:col0 + NCOL]
    xr = xs[col0:col0 + NCOL]
    yr = ys[row0:row0 + NROW]
    line = L.fit_edge_line(s, xr, yr, axis=AXIS)
    XX, YY = np.meshgrid(xr, yr)
    r = L.sfr_from_sites(s.ravel().astype(float), XX.ravel(), YY.ravel(),
                         line, BIN_UM, HALF_UM, TAPER)
    f, mtf = r["freq_cymm"], r["mtf"]
    floor_arr, flat = L.noise_floor_curve(f, mtf, BIN_UM, NB)
    fit = L.fit_fc(f, mtf, F_LO, F_HI)
    bound = L.signal_bound_curve(f, mtf, floor_arr, Z, RUN)
    reads = {}
    for fr in F_READ:
        i = int(np.argmin(np.abs(f - fr)))
        j0 = max(0, i - 1)
        reads[f"{fr:.2f}"] = dict(
            f=float(f[i]), mtf=float(mtf[i]), floor=float(floor_arr[i]),
            snr=float(mtf[i] / floor_arr[i]),
            run3=bool(np.all(mtf[j0:j0 + 3] > Z * floor_arr[j0:j0 + 3])))
    i40 = int(np.argmin(np.abs(f - F_FOCUS)))
    return dict(angle_deg=line["angle_deg"], resid_sd_px=line["resid_sd_px"],
                contrast=line["contrast"], lo_dn=line["lo_dn"],
                hi_dn=line["hi_dn"], mtf40=float(mtf[i40]),
                flat_floor=flat, bound=bound, reads=reads,
                min_bin_count=int(np.min(r["count"])), **fit)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stack")
    ap.add_argument("--which", default="G1")
    ap.add_argument("--tag", default="")
    args = ap.parse_args()

    files = sorted((ROOT / args.stack).glob("*.ARW"))
    rois = ROIS[args.stack]
    print(f"{args.stack}: {len(files)} frames, {len(rois)} ROIs, "
          f"plane {args.which}")
    recs = []
    t0 = time.time()
    for k, path in enumerate(files):
        active = L.load_active(path)
        sub, xs, ys = L.green_sites(active, args.which)
        for name, r0, c0 in rois:
            try:
                d = measure_roi(sub, xs, ys, r0, c0)
            except L.EdgeFitError as e:
                d = {"error": str(e)}
            d.update(roi=name, frame=k, file=path.name, row0=r0, col0=c0)
            recs.append(d)
        del active, sub
        if k % 5 == 0 or k == len(files) - 1:
            print(f"  frame {k:3d}/{len(files)-1}  "
                  f"{time.time()-t0:6.1f}s", flush=True)

    tag = args.tag or args.which
    p = OUT / f"s06_scan_{args.stack}_{tag}.json"
    p.write_text(json.dumps(recs, indent=1, default=float), encoding="utf-8")
    print(f"wrote {p}")


if __name__ == "__main__":
    main()
