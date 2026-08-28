r"""Flat-site band-0 SNR = signal var / noise var, per arm, from the split-half
decomposition. This is the number that says whether an arm is a good TRADE:
removing signal is acceptable only if it removes proportionally more noise.

  SNR ratio > 1  arm removes proportionally more noise than signal
  SNR ratio < 1  arm removes proportionally more SIGNAL than noise -- the arm
                 is a net loss at the very sites it was supposed to clean.
Paired bootstrap over tiles, float64 throughout.
"""
import argparse
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bandmetrics as bm                                           # noqa: E402
import nscale as ns                                                # noqa: E402
import sigref as sg                                                # noqa: E402
import splithalf as sh                                             # noqa: E402

OUT = r"C:\dev\strehl-out\V-BANDFLOOR\nscale"


def snr_ratio(s, n, s0, n0, seed=13, nboot=4000):
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(s), size=(nboot, len(s)))
    q = ((np.median(s[idx], 1) / np.maximum(np.median(n[idx], 1), 1e-30)) /
         np.maximum(np.median(s0[idx], 1) / np.maximum(np.median(n0[idx], 1), 1e-30), 1e-30))
    m = (np.median(s) / max(np.median(n), 1e-30)) / max(np.median(s0) / max(np.median(n0), 1e-30), 1e-30)
    return float(m), float(np.percentile(q, 2.5)), float(np.percentile(q, 97.5))


ap = argparse.ArgumentParser()
ap.add_argument("--subject", required=True)
ap.add_argument("--arms", required=True)
ap.add_argument("--pct", type=float, default=25.0)
ap.add_argument("--tile", type=int, default=128)
a = ap.parse_args()
bm.TILE = a.tile
arms = a.arms.split(",")

ge, cme, cfe = ns.load64(os.path.join(OUT, "%s__EVEN__%s.tiff" % (a.subject, arms[0])))
go, cmo, cfo = ns.load64(os.path.join(OUT, "%s__ODD__%s.tiff" % (a.subject, arms[0])))
flat, tex = sh.masks(ge, go, cme | cmo, a.pct)
y0, x0, ty, tx = sh.geom(ge.shape)
s0, n0 = sg.decomp(ge, go, flat, y0, x0, ty, tx)
ds0, dn0 = sg.decomp(ge, go, tex, y0, x0, ty, tx)
print("%s  flat-site band-0 SNR, flattest %g%% (%d tiles), clip %.4f%%"
      % (a.subject, a.pct, int(flat.sum()), 100 * max(cfe, cfo)))
print("  baseline FLAT SNR %.3f   DETAIL SNR %.3f"
      % (np.median(s0) / np.median(n0), np.median(ds0) / np.median(dn0)))
for arm in arms:
    pe = os.path.join(OUT, "%s__EVEN__%s.tiff" % (a.subject, arm))
    po = os.path.join(OUT, "%s__ODD__%s.tiff" % (a.subject, arm))
    if not (os.path.exists(pe) and os.path.exists(po)):
        print("  %-12s MISSING" % arm)
        continue
    gx, _, _ = ns.load64(pe)
    gy, _, _ = ns.load64(po)
    s, n = sg.decomp(gx, gy, flat, y0, x0, ty, tx)
    d, e = sg.decomp(gx, gy, tex, y0, x0, ty, tx)
    m = snr_ratio(s, n, s0, n0)
    md = snr_ratio(d, e, ds0, dn0)
    verdict = "NET GAIN" if m[1] > 1.0 else ("NET LOSS" if m[2] < 1.0 else "indistinct")
    print("  %-12s FLAT SNR x%.4f [%.4f,%.4f]  %-10s | DETAIL SNR x%.4f [%.4f,%.4f]"
          % (arm, m[0], m[1], m[2], verdict, md[0], md[1], md[2]))
