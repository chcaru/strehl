"""M116-promotion — CD1 calibration, after the registered plant FAILED.

CD1 required the instrument to recover a planted +0.50 px radial displacement
to within +/-0.10 px. It read -0.035, -0.290, -0.375, -0.055. It FAILED, and
that failure stands on the record.

The fault is MINE and it is provable from the documented convention WITHOUT
looking at the result, which is the only reason repairing it is legitimate
rather than fitting until green:

  1. SIGN. `warpmap.rs:14-30` documents every transform as a PULL:
     dst(p) = src(T(p)). My plant sampled at T(z) = (1+k)z, so a feature at
     source u lands at p = u/(1+k) -- it moves INWARD and red is imaged
     SMALLER. I planted -0.5 px and predicted +0.5 px. The measured sign was
     right; my prediction's sign was wrong.
  2. MAGNITUDE. I defined the plant at the CORNER (k = px/r_max) and then
     compared it against a measurement taken at an ANNULUS whose mid-radius is
     well inside the corner. The displacement of a radial rescale is k*r, so
     the correct expectation at normalised radius r is px*r, not px.

Both are arithmetic errors in my own bar. Neither is a property of the data.
This script re-states the calibration correctly and reports the FULL curve --
every annulus, against its own exact prediction -- rather than the single
number the failed bar rested on, so the instrument's accuracy is visible
rather than asserted.

Run: python ca_calibrate.py
"""

import json
import sys
from pathlib import Path

import numpy as np
import tifffile
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).parent))
from score_ca_disp import (ANNULI, NSECT, WIN, UPSAMPLE, MIN_STRUCT,
                           radial_displacement, load, highpass)
from skimage.registration import phase_cross_correlation

CA = Path(r"C:\dev\strehl-out\M116\ca")
SUBJECTS = ["bee-3-cpl", "flat-on-ruler-cpl",
            "tweezers-cpl", "flower-bud-with-background-fern-cpl"]
PLANT_PX = 0.50
TOL = 0.10          # the tolerance CD1 registered


def plant_radial_correct(a: np.ndarray, px: float) -> np.ndarray:
    """Displace R radially OUTWARD by `px` at the corner.

    A PULL: to make the channel appear LARGER by (1+k), the destination must
    sample INSIDE, at z/(1+k). This is the direction `compose` documents at
    optics.rs:225 -- "s = 1 + eps NOT 1/(1+eps)" -- read in the opposite
    direction, because here I am ADDING the aberration rather than removing it.
    """
    h, w = a.shape[:2]
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    k = px / float(np.hypot(cy, cx))
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    out = a.copy()
    out[:, :, 0] = ndimage.map_coordinates(
        a[:, :, 0],
        [cy + (yy - cy) / (1.0 + k), cx + (xx - cx) / (1.0 + k)],
        order=3, mode="nearest")
    return out


def plant_translation(a: np.ndarray, dx: float, dy: float) -> np.ndarray:
    """A pure translation of R. Constant everywhere, so it calibrates the
    sub-pixel accuracy of the correlator with no radius term to get wrong."""
    out = a.copy()
    out[:, :, 0] = ndimage.shift(a[:, :, 0], (dy, dx), order=3, mode="nearest")
    return out


def raw_shift_recovery(a: np.ndarray, want=(0.0, 0.5)):
    """Median raw (dy, dx) shift of R against G over all structured windows."""
    h, w = a.shape[:2]
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    rmax = float(np.hypot(cy, cx))
    r = WIN // 2
    dys, dxs = [], []
    for (lo, hi) in ANNULI:
        rad = 0.5 * (lo + hi) * rmax
        for k in range(NSECT):
            th = 2.0 * np.pi * k / NSECT
            py = int(round(cy + rad * np.sin(th)))
            px = int(round(cx + rad * np.cos(th)))
            if not (r <= py < h - r and r <= px < w - r):
                continue
            g = a[py - r:py + r, px - r:px + r, 1].astype(np.float64)
            c = a[py - r:py + r, px - r:px + r, 0].astype(np.float64)
            if float(highpass(g).std()) < MIN_STRUCT:
                continue
            s, _, _ = phase_cross_correlation(g, c, upsample_factor=UPSAMPLE,
                                              normalization=None)
            dys.append(-float(s[0]))
            dxs.append(-float(s[1]))
    return (float(np.median(dys)) if dys else float("nan"),
            float(np.median(dxs)) if dxs else float("nan"),
            len(dxs))


def main() -> int:
    out = {"plant_px": PLANT_PX, "tolerance_px": TOL, "subjects": {}}
    for s in SUBJECTS:
        p = CA / "measure" / f"{s}__OFF.tif"
        if not p.exists():
            continue
        print(f"== {s}")
        off = load(p)
        base = radial_displacement(off, 0)

        # --- CD1a: pure translation. No radius term can be got wrong. -------
        tr = plant_translation(off, 0.5, 0.0)
        dy, dx, n = raw_shift_recovery(tr)
        b_dy, b_dx, _ = raw_shift_recovery(off)
        rec_dx, rec_dy = dx - b_dx, dy - b_dy
        ok_tr = abs(rec_dx - 0.5) <= TOL and abs(rec_dy) <= TOL
        print(f"   translation plant (+0.500, 0.000) px -> recovered "
              f"({rec_dx:+.4f}, {rec_dy:+.4f}) over {n} windows   "
              f"{'PASS' if ok_tr else 'FAIL'}")
        del tr

        # --- CD1b: radial rescale, correct sign, per-annulus prediction -----
        pl = plant_radial_correct(off, PLANT_PX)
        got = radial_displacement(pl, 0)
        del pl
        rows, errs = [], []
        for b, g in zip(base, got):
            if not (np.isfinite(b["rd_px"]) and np.isfinite(g["rd_px"])):
                continue
            rmid = 0.5 * (b["r_lo"] + b["r_hi"])
            pred = PLANT_PX * rmid          # displacement of a rescale is k*r
            meas = g["rd_px"] - b["rd_px"]
            rows.append({"r_lo": b["r_lo"], "r_hi": b["r_hi"],
                         "predicted_px": pred, "recovered_px": meas,
                         "err_px": meas - pred})
            errs.append(abs(meas - pred))
            print(f"   r {b['r_lo']:.2f}-{b['r_hi']:.2f}  predicted {pred:+.4f}"
                  f"  recovered {meas:+.4f}  err {meas - pred:+.4f}")
        worst = float(max(errs)) if errs else float("nan")
        ok_rad = bool(errs) and worst <= TOL
        print(f"   worst |err| = {worst:.4f} px   "
              f"{'PASS' if ok_rad else 'FAIL'} at tol {TOL}")

        out["subjects"][s] = {
            "translation_recovered_dx": rec_dx, "translation_recovered_dy": rec_dy,
            "translation_pass": ok_tr, "translation_windows": n,
            "radial_rows": rows, "radial_worst_err_px": worst,
            "radial_pass": ok_rad,
        }
        del off

    dst = CA / "calibration.json"
    dst.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nwrote {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
