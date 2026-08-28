r"""Could the 'detail is preserved' reading be an artifact of ONE filter scale?

Part 14 measured mid-band energy with a DoG at sigma 1.4/2.8 and concluded the
gate-floor default removes noise, not detail. BUILD-PLUGIN reports the same
change costing -9.9% to -39.9% sharpness. Both cannot be right about the same
pixels, and the cheapest way for me to be wrong is to have looked at one
octave.

So: sweep the octave. At each scale, split flat from detailed territory on a
reference built from BOTH arms and report the ratio separately.

  If softening is real and I missed it, some scale reads detail << 1.
  If it is noise, detail stays ~1 at EVERY scale while flat falls at the fine
  scales only -- because photon noise is white and lives in the fine octaves.

Commissioned at every scale with the same planted denoise and planted
softening as gf_discriminate, so a scale that cannot see a softening is
disqualified rather than counted as evidence of absence.
"""
import os

import numpy as np
import tifffile
from scipy.ndimage import gaussian_filter, uniform_filter

import gf_measure as M

OUT = r"C:\dev\strehl-out\V-GATHER\gatefloor"
SIGMAS = [0.7, 1.4, 2.8, 5.6, 11.2]


def band(g, s):
    return gaussian_filter(g, s) - gaussian_filter(g, 2.0 * s)


def masks(ref, win):
    loc = gaussian_filter(ref, 1.0)
    var = uniform_filter(loc ** 2, win) - uniform_filter(loc, win) ** 2
    var = np.clip(var, 0, None)
    return var <= np.quantile(var, 0.30), var >= np.quantile(var, 0.90)


def ratio(gw, gm, ref, s):
    win = max(9, int(8 * s) | 1)
    flat, det = masks(ref, win)
    bw, bm = band(gw, s), band(gm, s)
    rf = np.sqrt(np.mean(bm[flat] ** 2)) / np.sqrt(np.mean(bw[flat] ** 2))
    rd = np.sqrt(np.mean(bm[det] ** 2)) / np.sqrt(np.mean(bw[det] ** 2))
    return float(rf), float(rd)


def commission():
    print("commissioning every scale (a blind scale proves nothing)\n")
    rng = np.random.default_rng(11)
    h = w = 800
    base = np.zeros((h, w))
    for i in range(0, w, 160):
        base[:, i:i + 80] = 0.4
    base = gaussian_filter(base, 1.0)
    detail = np.abs(base - gaussian_filter(base, 3.0)) > 1e-3
    signal = base + gaussian_filter(rng.standard_normal((h, w)), 0.9) * 0.03 * detail
    noise = rng.standard_normal((h, w)) * 0.02
    a = signal + noise
    print("%8s %18s %18s %s" % ("sigma", "DENOISE f/d", "SOFTEN f/d", "usable?"))
    ok = {}
    for s in SIGMAS:
        rf1, rd1 = ratio(a, signal + 0.5 * noise, signal, s)
        rf2, rd2 = ratio(a, gaussian_filter(signal, 1.3) + noise, signal, s)
        usable = (rd2 < 0.95) and (rd1 > 0.95)
        ok[s] = usable
        print("%8.1f  %7.4f/%7.4f  %7.4f/%7.4f  %s"
              % (s, rf1, rd1, rf2, rd2, "yes" if usable else "NO - blind"))
    return ok


def main():
    ok = commission()
    fw = os.path.join(OUT, "ms-leaf-white.tiff")
    fm = os.path.join(OUT, "ms-leaf-measured.tiff")
    if not (os.path.exists(fw) and os.path.exists(fm)):
        raise SystemExit("renders missing; nothing measured")
    gw = M.luma(tifffile.imread(fw))
    gm = M.luma(tifffile.imread(fm))
    ref = gaussian_filter(0.5 * (gw + gm), 1.5)
    print("\nleaf-2-cpl, white -> measured (the worst subject in Part 14)\n")
    print("%8s %10s %10s   %s" % ("sigma", "flat", "detail", "reading"))
    print("-" * 52)
    for s in SIGMAS:
        rf, rd = ratio(gw, gm, ref, s)
        if not ok[s]:
            note = "scale BLIND -- excluded"
        elif rd < 0.95:
            note = "DETAIL LOST"
        elif rf < 0.95:
            note = "denoise only"
        else:
            note = "inert"
        print("%8.1f %10.4f %10.4f   %s" % (s, rf, rd, note))
    print("\nA softening confined to one octave would show as detail << 1 at")
    print("that octave only. Noise removal shows as flat << 1 at fine scales")
    print("with detail ~1 everywhere.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
