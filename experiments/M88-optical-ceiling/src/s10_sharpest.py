"""s10: EXPLORATORY, post-hoc.  How sharp is the sharpest edge in the corpus?

The pre-registered ROIs all report 6-8 um of blur on top of diffraction.  That
is either the subject's own edge softness, residual defocus, or aberration.
This script asks a different, capture-level question: over a wide grid of
candidate edges and frames, what is the sharpest edge the corpus contains?

Everything here is labelled EXPLORATORY in the report.  It cannot rescue the
pre-registered verdict and is not used to.  It exists to say what capture
would unblock the measurement.
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
BIN_UM, TAPER = 0.64, 0.10
HALF_UM = 64.0
CORE_UM = 24.0
F_LO, F_HI = 10.0, 150.0
NB = (250.0, 380.0)
NROW, NCOL = 240, 600


def scan_frame(sub, xs, ys, stride_r=240, stride_c=600):
    out = []
    H, W = sub.shape
    for r0 in range(0, H - NROW + 1, stride_r):
        for c0 in range(0, W - NCOL + 1, stride_c):
            s = sub[r0:r0 + NROW, c0:c0 + NCOL].astype(float)
            xr, yr = xs[c0:c0 + NCOL], ys[r0:r0 + NROW]
            try:
                line = L.fit_edge_line(s, xr, yr, axis="horizontal")
            except L.EdgeFitError:
                continue
            if not (0.4 <= abs(line["angle_deg"]) <= 12.0):
                continue
            if line["contrast"] < 500.0 or line["resid_sd_px"] > 0.6:
                continue
            XX, YY = np.meshgrid(xr, yr)
            try:
                r = L.sfr_from_sites2(s.ravel(), XX.ravel(), YY.ravel(), line,
                                      BIN_UM, HALF_UM, TAPER, core_um=CORE_UM)
            except L.EdgeFitError:
                continue
            f, mtf = r["freq_cymm"], r["mtf"]
            try:
                fl, flat = L.noise_floor_curve(f, mtf, BIN_UM, NB)
            except L.EdgeFitError:
                continue
            fit = L.fit_fc(f, mtf, F_LO, F_HI)
            i40 = int(np.argmin(np.abs(f - 40.0)))
            i86 = int(np.argmin(np.abs(f - 86.30)))
            i97 = int(np.argmin(np.abs(f - 97.66)))
            out.append(dict(row0=r0, col0=c0, angle=line["angle_deg"],
                            contrast=line["contrast"],
                            resid=line["resid_sd_px"],
                            mtf40=float(mtf[i40]), fc=fit["fc_cymm"],
                            sigma=fit["sigma_um"], amp=fit["amp"],
                            mtf86=float(mtf[i86]), fl86=float(fl[i86]),
                            mtf97=float(mtf[i97]), fl97=float(fl[i97]),
                            flat=flat,
                            bound=L.signal_bound_curve(f, mtf, fl, 3.0, 3)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stack")
    ap.add_argument("--every", type=int, default=3)
    args = ap.parse_args()
    files = sorted((ROOT / args.stack).glob("*.ARW"))
    recs = []
    t0 = time.time()
    for k in range(0, len(files), args.every):
        active = L.load_active(files[k])
        sub, xs, ys = L.green_sites(active, "G1")
        for d in scan_frame(sub, xs, ys):
            d.update(frame=k, stack=args.stack)
            recs.append(d)
        del active, sub
        print(f"  frame {k:3d}: cumulative {len(recs):5d} edges  "
              f"{time.time()-t0:6.1f}s", flush=True)
    p = OUT / f"s10_sharpest_{args.stack}.json"
    p.write_text(json.dumps(recs, indent=1, default=float), encoding="utf-8")
    if recs:
        recs.sort(key=lambda d: -d["mtf40"])
        print(f"\ntop 12 by MTF(40 cy/mm), stack {args.stack}:")
        print(f"{'frm':>4} {'row0':>5} {'col0':>5} {'ang':>6} {'con':>6} "
              f"{'mtf40':>6} {'fc':>7} {'sig':>6} {'amp':>5} {'M86':>7} "
              f"{'f86':>7} {'M97':>7} {'f97':>7}")
        for d in recs[:12]:
            print(f"{d['frame']:4d} {d['row0']:5d} {d['col0']:5d} "
                  f"{d['angle']:+6.2f} {d['contrast']:6.0f} {d['mtf40']:6.3f} "
                  f"{d['fc']:7.2f} {d['sigma']:6.2f} {d['amp']:5.2f} "
                  f"{d['mtf86']:7.4f} {d['fl86']:7.4f} {d['mtf97']:7.4f} "
                  f"{d['fl97']:7.4f}")
    print(f"wrote {p}")


if __name__ == "__main__":
    main()
