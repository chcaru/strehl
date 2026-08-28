r"""Is the acuity loss REMOVED NOISE (good) or REMOVED DETAIL (bad)?

Frame averaging lowers mid-band energy two ways and they mean opposite things:

  denoise  the gate averages more frames, photon noise falls, mid-band energy
           falls, and NO real structure is lost. Acuity is a worse number and
           the picture is better.
  soften   the gate averages frames that disagree because they are focused at
           different depths, and real detail is destroyed.

A single global acuity number cannot tell these apart, so this splits the frame
by local structure measured on a reference that privileges NEITHER arm, and
reports the ratio separately in flat and detailed territory.

  denoise predicts  ratio << 1 in FLAT, ratio ~= 1 in DETAIL
  soften  predicts  ratio << 1 in DETAIL as well

Commissioned with both a planted denoise and a planted softening, because a
discriminator that has only ever seen one of them cannot be known to separate
them.
"""
import json
import os
import sys

import numpy as np
import tifffile
from scipy.ndimage import gaussian_filter, uniform_filter

import gf_measure as M

OUT = r"C:\dev\strehl-out\V-GATHER\gatefloor"


def regions(ref, q_flat=0.30, q_detail=0.90):
    """Flat and detailed masks from a NEUTRAL reference (mean of both arms,
    blurred so neither arm's noise defines the segmentation)."""
    loc = gaussian_filter(ref, 1.0)
    var = uniform_filter(loc ** 2, 33) - uniform_filter(loc, 33) ** 2
    var = np.clip(var, 0, None)
    lo = np.quantile(var, q_flat)
    hi = np.quantile(var, q_detail)
    return var <= lo, var >= hi


def band_rms(g, mask, sigma=1.4):
    b = gaussian_filter(g, sigma) - gaussian_filter(g, 2.0 * sigma)
    v = b[mask]
    if v.size == 0:
        return float("nan")
    return float(np.sqrt(np.mean(v ** 2)))


def split_ratio(gw, gm, ref):
    flat, det = regions(ref)
    rf = band_rms(gm, flat) / band_rms(gw, flat)
    rd = band_rms(gm, det) / band_rms(gw, det)
    return rf, rd, int(flat.sum()), int(det.sum())


def commission():
    print("commissioning the discriminator\n")
    rng = np.random.default_rng(3)
    h = w = 700
    base = np.zeros((h, w))
    # Flat runs must be WIDER than the 33 px variance window or no window is
    # ever purely flat and the "flat" mask is really "near an edge". At period
    # 40/width 20 the DENOISE arm read flat=0.9161 when a pure halving of
    # noise must read ~0.5; that was the fixture, not the instrument.
    for i in range(0, w, 120):
        base[:, i:i + 60] = 0.4
    base = gaussian_filter(base, 1.0)
    texture = gaussian_filter(rng.standard_normal((h, w)), 0.9) * 0.03
    detail_mask = np.zeros((h, w), bool)
    detail_mask[:, :] = np.abs(base - gaussian_filter(base, 3.0)) > 1e-3
    signal = base + texture * detail_mask
    noise = rng.standard_normal((h, w)) * 0.02
    arm_w = signal + noise
    ok = True

    # PLANTED DENOISE: same signal, half the noise. Detail untouched.
    arm_dn = signal + 0.5 * noise
    rf, rd, nf, nd = split_ratio(arm_w, arm_dn, signal)
    print("  DENOISE   flat %0.4f  detail %0.4f   (want flat<<1, detail~1)"
          % (rf, rd))
    if not (rf < 0.75 and rd > 0.90):
        ok = False
        print("    FAIL: discriminator did not read a pure denoise correctly")

    # PLANTED SOFTEN: signal blurred, noise identical. Detail destroyed.
    arm_sf = gaussian_filter(signal, 1.3) + noise
    rf2, rd2, _, _ = split_ratio(arm_w, arm_sf, signal)
    print("  SOFTEN    flat %0.4f  detail %0.4f   (want detail<<1)"
          % (rf2, rd2))
    if not (rd2 < 0.90):
        ok = False
        print("    FAIL: discriminator did not read a pure softening")

    # SEPARATION: the two must be distinguishable in DETAIL territory.
    print("  SEPARATION detail %0.4f (denoise) vs %0.4f (soften)  gap %0.4f"
          % (rd, rd2, rd - rd2))
    if not (rd - rd2 > 0.05):
        ok = False
        print("    FAIL: denoise and soften are not separable")

    # NULL
    rf3, rd3, _, _ = split_ratio(arm_w, arm_w.copy(), signal)
    print("  NULL      flat %0.6f  detail %0.6f   (want exactly 1)"
          % (rf3, rd3))
    if not (rf3 == 1.0 and rd3 == 1.0):
        ok = False
        print("    FAIL: null is not exactly unity")
    print("\n  commissioning %s\n" % ("PASSED" if ok else "FAILED"))
    return ok


def main():
    if not commission():
        raise SystemExit("discriminator failed commissioning; no verdict")
    subs = json.load(open("gatefloor.json"))
    print("%-22s %9s %9s %10s  %s"
          % ("subject", "flat", "detail", "d b0 avg", "reading"))
    print("-" * 68)
    rows = []
    for r in subs:
        s = r["subject"]
        fw = os.path.join(OUT, "%s--white.tiff" % s)
        fm = os.path.join(OUT, "%s--measured.tiff" % s)
        if not (os.path.exists(fw) and os.path.exists(fm)):
            continue
        gw = M.luma(tifffile.imread(fw))
        gm = M.luma(tifffile.imread(fm))
        ref = gaussian_filter(0.5 * (gw + gm), 1.5)
        rf, rd, nf, nd = split_ratio(gw, gm, ref)
        db = (r.get("avg_b0_measured") or 0) - (r.get("avg_b0_white") or 0)
        if not np.isfinite(rd):
            reading = "REFUSED (no detail territory)"
        elif rd < 0.98:
            reading = "DETAIL LOST"
        elif rf < 0.98:
            reading = "denoise only"
        else:
            reading = "inert"
        print("%-22s %9.4f %9.4f %+9.1f pts  %s" % (s, rf, rd, db, reading))
        rows.append({"subject": s, "flat": rf, "detail": rd, "d_b0": db,
                     "reading": reading, "n_flat": nf, "n_detail": nd})
        del gw, gm, ref
    json.dump(rows, open("gatefloor-split.json", "w"), indent=1)
    print("\nwrote gatefloor-split.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
