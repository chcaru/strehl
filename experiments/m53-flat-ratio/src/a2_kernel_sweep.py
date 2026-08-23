"""M53 step 2 -- choose the high-pass box side on evidence, not on inheritance.

M41 used a 9x9 box.  A box high-pass leaves whatever scene structure survives
in its stop band, so the statistic's floor -- and therefore the largest noise
explosion it can be blind to -- is set by the box side.  This measures that
floor directly on both of M41's real ROIs:

    contamination(w) = hp_sd(w) / (gain(w) * sigma_model)

where gain(w) = sqrt(1 - 1/w^2) is the derived white-noise gain of the
`x - box_w(x)` operator and sigma_model is the calibrated temporal per-sample
sigma at the ROI's own mean level.  Rule 10: sigma_model is TEMPORAL, so this
is not an equality claim.  It is a bound -- a spatial high-pass sd cannot be
below the noise it contains, so any excess over 1.0 is residual scene, and the
excess is exactly the factor by which a ratio of two such sds under-reports a
large noise explosion.

The counter-pressure is real and is measured too: a narrower box is a weaker
low-pass, so on the DETAIL ROI it must still see structure, or the statistic
has stopped being a noise statistic and become a resolution statistic.

Read-only corpora are never written.  Rule 32: rawpy views copied inside `with`.
"""
import os
import sys
import glob
import json

import numpy as np
import rawpy
from scipy.ndimage import uniform_filter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")
os.makedirs(OUT, exist_ok=True)

BLACK = 512.0
SIDES = (3, 5, 7, 9, 11, 15, 21, 27)

# M41's out/rois_b.json, with a6_real.py's `max(PAD, .)` clamp applied to y.
#
# `g` is M41's value, DELIBERATELY, so this sweep sits in M41's frame of
# reference and the reconciliation in a1 stays like-for-like. For 109MSDCF
# (ISO 160) M41's g is also the shipped one. For 119MSDCF it is NOT: 50/436.8
# is the ISO-50 gain that SYNTHESIS fact 550 / M25 fact 200 corrected to
# `max(ISO, 100)/436.8`, i.e. exactly 2x larger, because ISO 50 on this body is
# an extended (pull) ISO that reads out at base-ISO gain.
#
# `g_shipped` is what the code actually uses today. Both contaminations are
# printed, because this artifact must not be readable as a post-fix number.
STACKS = {
    "109MSDCF": dict(dir=r"C:\dev\macro\test\109MSDCF", g=0.3663003663003663,
                     g_shipped=0.3663003663003663,
                     rn_e=4.2, flat=(1356, 32, 512, 512),
                     detail=(2215, 699, 512, 512)),
    "119MSDCF": dict(dir=r"C:\dev\macro\test\119MSDCF", g=0.11446886446886446,
                     g_shipped=0.22893772893772893,
                     rn_e=4.2, flat=(1396, 32, 512, 512),
                     detail=(2251, 800, 512, 512)),
}


def quad_green_roi(path, roi):
    x, y, w, h = roi
    with rawpy.imread(path) as r:
        v = r.raw_image_visible
        g1 = v[2 * y:2 * (y + h):2, 2 * x + 1:2 * (x + w) + 1:2].astype(np.float32)
        g2 = v[2 * y + 1:2 * (y + h) + 1:2, 2 * x:2 * (x + w):2].astype(np.float32)
    return 0.5 * (g1 + g2) - BLACK


def hp_sd_valid(a, w):
    r = w // 2
    resid = a - uniform_filter(a, w)
    return float(resid[r:a.shape[0] - r, r:a.shape[1] - r].std())


def model_sigma(mean, g, rn_e):
    """Green-luma temporal sigma: (G1+G2)/2 halves the variance of one sample."""
    return float(np.sqrt(0.5 * (g * max(mean, 0.0) + (rn_e * g) ** 2)))


def main():
    res = {}
    for name, info in STACKS.items():
        files = sorted(glob.glob(os.path.join(info["dir"], "*.ARW")))
        mid = len(files) // 2
        flat = quad_green_roi(files[mid], info["flat"])
        det = quad_green_roi(files[mid], info["detail"])
        sf = model_sigma(float(flat.mean()), info["g"], info["rn_e"])
        sd = model_sigma(float(det.mean()), info["g"], info["rn_e"])
        sf_shipped = model_sigma(float(flat.mean()), info["g_shipped"],
                                 info["rn_e"])
        stale = info["g"] != info["g_shipped"]
        print(f"\n=== {name}: {len(files)} frames, middle {mid}")
        if stale:
            print(f"    !! M41 gain {info['g']:.5f} DN/e- is the STALE ISO-50 value. "
                  f"Shipped today: {info['g_shipped']:.5f}")
            print(f"    !! (SYNTHESIS fact 550 / M25 fact 200: ISO 50 is an extended "
                  f"ISO and reads out at base-ISO gain.)")
            print(f"    !! model sigma {sf:.3f} -> {sf_shipped:.3f} DN, so every "
                  f"contamination below divides by {sf_shipped/sf:.4f}x.")
        print(f"    flat   mean {flat.mean():8.2f} DN  raw sd {flat.std():9.3f} DN  "
              f"model sigma {sf:6.3f} DN  -> raw sd / sigma {flat.std()/sf:7.2f}x")
        print(f"    detail mean {det.mean():8.2f} DN  raw sd {det.std():9.3f} DN  "
              f"model sigma {sd:6.3f} DN")
        print("     w    gain    flat hp_sd  contamination   detail hp_sd  "
              "detail/flat   contam@shipped g")
        rows = []
        for w in SIDES:
            gain = float(np.sqrt(1.0 - 1.0 / (w * w)))
            hf, hd = hp_sd_valid(flat, w), hp_sd_valid(det, w)
            cont = hf / (gain * sf)
            cont_shipped = hf / (gain * sf_shipped)
            rows.append(dict(w=w, gain=gain, flat_hp=hf, detail_hp=hd,
                             contamination=cont,
                             contamination_shipped_gain=cont_shipped))
            print(f"    {w:2d}  {gain:.6f}  {hf:10.4f}  {cont:12.4f}x  "
                  f"{hd:12.3f}  {hd/hf:10.2f}x  {cont_shipped:16.4f}x")
        res[name] = dict(flat_mean=float(flat.mean()), flat_raw_sd=float(flat.std()),
                         detail_raw_sd=float(det.std()),
                         gain_m41=info["g"], gain_shipped=info["g_shipped"],
                         sigma_flat=sf, sigma_flat_shipped=sf_shipped,
                         sigma_detail=sd, rows=rows)

    with open(os.path.join(OUT, "a2_kernel_sweep.json"), "w") as fh:
        json.dump(res, fh, indent=2)
    print(f"\nwrote {os.path.join(OUT, 'a2_kernel_sweep.json')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
