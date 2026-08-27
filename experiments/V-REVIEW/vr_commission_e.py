r"""ARM E, re-run: why the first chroma ladder read flat, and what it takes to move it.

vr_commission.py ARM E planted orch_chroma's own commissioning ladder
(0.0005-0.008 of luma, 150 px) into foam's real chroma window and the statistic
did not move. That is not a broken instrument, it is a ladder far below the
scene: the statistic is an RMS, so a plant p adds to a subject reading s as
sqrt(s^2 + p^2). foam reads s = 0.0325 and the largest rung, once band-passed,
carries p ~ 0.002 -- an increment of p^2/2s = 6e-5, under the printed digit.

So this arm does two things the first could not:
  E1  the same ladder on a QUIET real master window, where orch_chroma's own
      null-scene commissioning says it must respond;
  E2  a ladder scaled to foam's own reading, which is what "could a defect hide
      inside this number" actually asks;
  E3  prints the band-passed rms of the plant itself, so the predicted
      quadrature sum can be checked against the measured one -- an instrument
      that matches its own prediction is commissioned, one that merely rises is
      not.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vr_lib as V                                            # noqa: E402

CWIN = V.CWIN


def plant(crop, amp, period=150.0):
    yy, xx = np.mgrid[0:crop.shape[0], 0:crop.shape[1]].astype(np.float64)
    blob = np.sin(2 * np.pi * xx / period) * np.sin(2 * np.pi * yy / period)
    ylum = 0.299 * crop[..., 0] + 0.587 * crop[..., 1] + 0.114 * crop[..., 2]
    img = crop.copy()
    img[..., 0] += ylum * amp * blob
    img[..., 2] -= ylum * amp * blob
    return img


def ladder(name, crop, amps):
    c0 = V.gate_chroma(crop.astype(np.float32), at=(0, 0))["chroma"]
    print("  %s   unplanted chroma %.6f" % (name, c0))
    ok, prev = True, c0
    for amp in amps:
        img = plant(crop, amp)
        r = V.gate_chroma(img.astype(np.float32), at=(0, 0))["chroma"]
        # the plant alone, through the same band-pass: its own rms
        p = V.gate_chroma((plant(np.full_like(crop, 10000.0), amp)).astype(np.float32),
                          at=(0, 0))["chroma"]
        pred = float(np.hypot(c0, p))
        print("    amp %.4f  chroma %.6f  plant alone %.6f  quadrature predicts %.6f"
              "  measured/predicted %.4f  rises %s"
              % (amp, r, p, pred, r / pred, r > prev))
        ok = ok and r > prev
        prev = r
    return ok


def main():
    print("E1  quiet real master window (couch-fibers-cpl, gate chroma 0.0042)")
    rgb = V.read_rgb(V.master_path("couch-fibers-cpl"))
    c = V.gate_chroma(rgb)
    crop = rgb[c["y"]:c["y"] + CWIN, c["x"]:c["x"] + CWIN].astype(np.float64).copy()
    del rgb
    ok1 = ladder("couch-fibers-cpl", crop, (0.0005, 0.001, 0.002, 0.004, 0.008))

    print("\nE2  foam's own window, ladder scaled to what foam actually reads")
    rgb = V.read_rgb(V.master_path("foam"))
    c = V.gate_chroma(rgb)
    crop = rgb[c["y"]:c["y"] + CWIN, c["x"]:c["x"] + CWIN].astype(np.float64).copy()
    del rgb
    ok2 = ladder("foam", crop, (0.01, 0.02, 0.04, 0.08, 0.16))

    print("\nARM E1 %s   ARM E2 %s" % ("PASS" if ok1 else "FAIL", "PASS" if ok2 else "FAIL"))
    print("\nCONSEQUENCE FOR THE ADJUDICATION, stated here rather than discovered later:")
    print("chroma is an RMS. If a master reads m and its source arm reads s with m > s,")
    print("the component the merge could have ADDED is at most sqrt(m^2 - s^2), and that")
    print("is the number to quote -- not the ratio m/s, which exaggerates a small")
    print("addition on top of a large subject reading and understates a large one.")


if __name__ == "__main__":
    main()
