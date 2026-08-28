r"""THE ARM rimcommission.py NEVER RAN: a SHARP edge that has NO rim.

rimcommission.py has a sensitivity ladder (plant a rim, the score must rise) and
two arms it calls controls, neither of which is a sharp rim-free image:

  FLOOR      tests the gaussian sigma-3 SMOOTHED base. Smoothing removes the
             rim AND the shoulder texture, so it cannot show what a sharp
             rim-free edge reads.
  NOTALWAYS  tests the unmodified master -- the very thing under test. If the
             master has a false positive, this arm asserts it away.

So the false-positive rate of this axis has never been measured. This measures
it, on edges that are MONOTONE BY CONSTRUCTION: a step convolved with a
Gaussian is monotone, and adding a zero-mean field to its shoulders does not
create a rim, it creates roughness. Anything the axis reads above zero here is
a false positive with no rim to find.

BOTH ARMS. Arm A sweeps shoulder roughness with no rim. Arm B holds roughness
fixed and sweeps a PLANTED rim of known amplitude and known width, so the
reading can be converted back into the amplitude it implies. An instrument that
only ever saw arm B is the combination this project has already shipped once.

MATCHED CONTROL in every rung: roughness 0 with rim 0 must read ~0.
"""
import io
import json
import os
import sys

import numpy as np
from scipy import ndimage

import vr_lib as V
import rimaxis
import rimv6

OUT = os.path.join(V.SCRATCH, "specificity.json")
N = 2048
SEED = 909


def scene(seed=SEED):
    """Random straight monotone edges. A blurred step is monotone, so no rim
    exists anywhere in this image by construction."""
    rng = np.random.default_rng(seed)
    img = np.zeros((N, N), np.float32)
    step = 0.30
    for k in range(28):
        th = rng.uniform(0, np.pi)
        c = rng.uniform(0.2, 0.8)
        yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
        d = (np.cos(th) * xx + np.sin(th) * yy) / N
        img += step * (d > c).astype(np.float32)
        del yy, xx, d
    img = ndimage.gaussian_filter(img, 1.2).astype(np.float32)
    return img


def roughen(img, amp, seed):
    """Band-limited zero-mean field. Band-limited, not white: a demosaiced
    sensor image is band-limited, and white noise would let the max-of-6 see
    six independent draws where a real image gives it roughly two."""
    rng = np.random.default_rng(seed)
    n = rng.normal(0.0, 1.0, img.shape).astype(np.float32)
    n = ndimage.gaussian_filter(n, 0.8)
    n /= n.std()
    return (img + amp * n).astype(np.float32)


def plant_rim(img, amp, at=3.0, wid=1.5):
    """A rim at a KNOWN offset and width: amp * exp(-(d-at)^2/2wid^2) added on
    the BRIGHT side of every edge, where d is the signed distance from the
    edge in px along the gradient. Built from the image's own gradient so it
    lands on the real edges, and windowed so it cannot reach t=+9..+12 and
    contaminate the normalising reference."""
    sm = ndimage.gaussian_filter(img, 1.2)
    gy, gx = np.gradient(sm)
    mag = np.hypot(gx, gy)
    # distance from the ridge of |grad|, signed by the gradient direction
    edge = mag > np.percentile(mag, 99.0)
    d = ndimage.distance_transform_edt(~edge).astype(np.float32)
    bright = sm > ndimage.uniform_filter(sm, 25)
    bump = np.exp(-((d - at) ** 2) / (2.0 * wid * wid)).astype(np.float32)
    bump[d > 8.0] = 0.0
    return (img + amp * bump * bright).astype(np.float32)


def score(g):
    clip = np.zeros(g.shape, bool)
    rec, sel, ref, em = V.run_pipeline(g, clip, ntile=40)
    if "corrected_bright" not in rec:
        return None, rec
    return rec["corrected_bright"], rec


def main():
    doc = {}
    base = scene()
    step_dn = 0.30
    print("SYNTHETIC SCENE: 28 monotone blurred steps, step %.2f in [0,1]." % step_dn)

    print("\n== ARM A -- SPECIFICITY. No rim exists. Sweep shoulder roughness. ==")
    print("   %8s %10s %12s %12s %10s %8s" % ("rough", "rough/step",
          "corrected", "med-then-max", "shoulder", "verdict"))
    doc["A"] = []
    for amp in (0.0, 0.003, 0.006, 0.012, 0.024, 0.048, 0.090):
        g = roughen(base, amp, seed=SEED + 1)
        c, rec = score(g)
        if c is None:
            print("   %8.4f  REFUSED %s" % (amp, rec.get("refused")))
            doc["A"].append(dict(amp=amp, refused=rec.get("refused")))
            continue
        cm = rec["coh_master"]
        v = V.verdict(rec)[0]
        print("   %8.4f %10.4f %11.3f%% %11.3f%% %10.4f %8s  (n=%d)"
              % (amp, amp / step_dn, 100 * c, 100 * cm["median_then_max"],
                 cm["shoulder_sd_median"], v, rec["n_sel"]))
        doc["A"].append(dict(amp=amp, corrected=c, verdict=v,
                             med_then_max=cm["median_then_max"],
                             shoulder_sd=cm["shoulder_sd_median"],
                             n=rec["n_sel"]))

    print("\n== ARM B -- SENSITIVITY. Roughness fixed at 0.012 (~4%% of step).")
    print("   Plant a rim of KNOWN amplitude at t=+3px, width 1.5px. ==")
    print("   %8s %10s %12s %12s %8s" % ("rim amp", "rim/step", "corrected",
                                          "med-then-max", "verdict"))
    doc["B"] = []
    rough = roughen(base, 0.012, seed=SEED + 1)
    for amp in (0.0, 0.003, 0.006, 0.012, 0.024, 0.048, 0.090):
        g = plant_rim(rough, amp)
        c, rec = score(g)
        if c is None:
            print("   %8.4f  REFUSED %s" % (amp, rec.get("refused")))
            doc["B"].append(dict(amp=amp, refused=rec.get("refused")))
            continue
        cm = rec["coh_master"]
        v = V.verdict(rec)[0]
        print("   %8.4f %10.4f %11.3f%% %11.3f%% %8s  (n=%d)"
              % (amp, amp / step_dn, 100 * c, 100 * cm["median_then_max"], v,
                 rec["n_sel"]))
        doc["B"].append(dict(amp=amp, corrected=c, verdict=v,
                             med_then_max=cm["median_then_max"], n=rec["n_sel"]))

    print("\n== ARM C -- SPECIFICITY AT A REAL SUBJECT'S ROUGHNESS.")
    print("   Roughness set to the shoulder sd measured on each named master,")
    print("   still with NO rim. ==")
    doc["C"] = []
    for tag, sd in (("109MSDCF PASS", 0.0598), ("bee-1 FAIL", 0.0795),
                    ("lavendar FAIL", 0.1035), ("113MSDCF FAIL", 0.1644),
                    ("leaf-2 FAIL", 0.3015)):
        amp = sd * step_dn
        g = roughen(base, amp, seed=SEED + 1)
        c, rec = score(g)
        if c is None:
            print("   %-16s REFUSED %s" % (tag, rec.get("refused")))
            continue
        cm = rec["coh_master"]
        print("   %-16s target sd %.4f -> got %.4f   corrected %+7.3f%%  %s"
              % (tag, sd, cm["shoulder_sd_median"], 100 * c, V.verdict(rec)[0]))
        doc["C"].append(dict(tag=tag, target_sd=sd, corrected=c,
                             got_sd=cm["shoulder_sd_median"]))

    json.dump(doc, io.open(OUT, "w", encoding="utf-8"), indent=1)
    print("\nwrote %s" % OUT)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
