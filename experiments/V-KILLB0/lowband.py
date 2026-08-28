"""V-KILLB0 conservative low-band scan across all 19 subjects.

Only five subjects have a measured boundary, and ORCH correction #4 forbids
transferring one subject's band to another.  So instead of guessing the other
fourteen, this scores every subject in 0.060-0.140 cyc/px, which lies BELOW the
lowest boundary V-LINEAR measured (0.17 on flower-bud-alone-cpl) and therefore
below every boundary in the document.

Stated assumption, and it is an assumption: a subject whose boundary fell below
0.14 would have essentially no qualified detail at all.  For the five measured
subjects the assumption is verified, not assumed.  Any subject that loses
energy at STRUCTURED pixels in this band is losing qualified signal.

Structure is selected at 0.030-0.085 cyc/px (below all boundaries).
Ratios are within-subject arm ratios only -- no cross-subject ratio is formed.
"""
import glob
import os
import sys

import numpy as np
from scipy.ndimage import gaussian_filter

import bandprobe as bp

F0, F1 = 0.060, 0.140
MEASURED = {"bee-1-cpl": 0.48, "113MSDCF": 0.25, "119MSDCF": 0.25,
            "leaf-2-cpl": 0.20, "flower-bud-alone-cpl": 0.17}


def rb(img, f0, f1):
    a = np.fft.rfft2(img.astype(np.float32))
    fy = np.fft.fftfreq(img.shape[0])[:, None]
    fx = np.fft.rfftfreq(img.shape[1])[None, :]
    r = np.sqrt(fy * fy + fx * fx)
    a *= ((r >= f0) & (r < f1))
    return np.fft.irfft2(a, s=img.shape)


def main():
    da, db = sys.argv[1], sys.argv[2]
    names = sorted(os.path.basename(p)[:-5] for p in glob.glob(os.path.join(db, "*.tiff")))
    print(f"band {F0}-{F1} cyc/px, below every boundary in V-LINEAR-BANDS.md")
    print(f"{'subject':<26} {'bnd':>5} {'STRUCT B/A':>11} {'rho':>7} "
          f"{'A DN':>8} {'B DN':>8} {'FLAT B/A':>9} {'medianDN':>9} {'clip%':>6} {'blk%':>6}")
    for nm in names:
        pa = os.path.join(da, nm + ".tiff")
        if not os.path.exists(pa):
            continue
        la = bp.channels(bp.load(pa))["L"]
        lb = bp.channels(bp.load(os.path.join(db, nm + ".tiff")))["L"]
        sel = gaussian_filter(np.abs(rb(la, 0.030, 0.085)), 3.0)
        st = sel >= np.percentile(sel, 75)
        fl = sel < np.percentile(sel, 25)
        pa_, pb_ = rb(la, F0, F1), rb(lb, F0, F1)
        out = []
        for m in (st, fl):
            a, b = pa_[m].astype(np.float64), pb_[m].astype(np.float64)
            a -= a.mean(); b -= b.mean()
            ea, eb = np.sqrt((a*a).mean()), np.sqrt((b*b).mean())
            out.append((eb/ea, (a*b).mean()/(ea*eb), ea, eb))
        bnd = f"{MEASURED[nm]:.2f}" if nm in MEASURED else "  ?"
        print(f"{nm:<26} {bnd:>5} {out[0][0]:11.4f} {out[0][1]:7.4f} "
              f"{out[0][2]:8.1f} {out[0][3]:8.1f} {out[1][0]:9.4f} "
              f"{np.median(la):9.0f} {100*(la>=65000).mean():6.2f} {100*(la<=200).mean():6.2f}")


if __name__ == "__main__":
    main()
