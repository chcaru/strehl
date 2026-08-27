r"""COMMISSIONING for the V-REVIEW master-vs-source instrument.

Five arms, and the instrument is refused if any fails:

  A IDENTITY      the master pulled through the real warp path with A = I must
                  return the statistic bit-identically -> ratio exactly 1.0000.
  B REGISTRATION  a synthetic similarity of known scale/rotation/shift planted
                  into a copy of the master must be recovered; the residual sets
                  how well the arms can be said to share a window at all.
  C WARP BIAS     the same master measured through a real-sized geometry change
                  (downscale to the source's cover ratio, warp back) -- the
                  SPREAD this produces is the floor below which two numbers in
                  the report may not be distinguished.
  D CONVICT       a blotch field planted at 0.25-4 sigma into a REAL master
                  window must raise the ratio monotonically above 1. An
                  instrument that cannot convict a planted defect cannot acquit.
  E CONVICT-CHROMA  the same for the chroma statistic.
"""
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vr_lib as V                                            # noqa: E402

SUBJ = "foam"
WIN = V.BWIN          # 900
CWIN = V.CWIN         # 1200


def blot_field(shape, rng, cell=64):
    """The plant, modelled on orch_blotch.commission: a coarse random field
    bilinearly upsampled, normalised to unit sd, so its scale sits inside the
    50-400 px band the statistic reads."""
    h, w = shape
    coarse = rng.normal(0, 1, (h // cell + 2, w // cell + 2)).astype(np.float32)
    f = cv2.resize(coarse, (w, h), interpolation=cv2.INTER_LINEAR)
    return (f - f.mean()) / max(float(np.std(f)), 1e-6)


def main():
    rng = np.random.default_rng(7)
    rgb = V.read_rgb(V.master_path(SUBJ))
    lum = V.lum_of(rgb)
    b = V.gate_blotch(rgb)
    c = V.gate_chroma(rgb)
    y, x = b["y"], b["x"]
    cy, cx = c["y"], c["x"]
    print("subject %s   blotch window (%d,%d)  chroma window (%d,%d)" % (SUBJ, y, x, cy, cx))
    print("direct: blotch %.5f  band %.1f noise %.1f mean %.1f | chroma %.6f"
          % (b["contrast"], b["band"], b["noise"], b["mean"], c["chroma"]))

    print("\nARM A  IDENTITY -- the real warp path with A = I")
    A = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    w_rgb = V.warp_window(rgb, A, y, x, WIN)
    r_id = V.blotch_ratio(V.lum_of(w_rgb))[0]
    cw = V.warp_window(rgb, A, cy, cx, CWIN)
    c_id = V.gate_chroma(cw, at=(0, 0))["chroma"]
    print("  blotch  direct %.6f   through warp %.6f   ratio %.6f" %
          (b["contrast"], r_id, r_id / b["contrast"]))
    print("  chroma  direct %.6f   through warp %.6f   ratio %.6f" %
          (c["chroma"], c_id, c_id / c["chroma"]))
    ok_a = abs(r_id / b["contrast"] - 1) < 1e-6 and abs(c_id / c["chroma"] - 1) < 1e-6
    print("  ARM A %s" % ("PASS" if ok_a else "FAIL"))

    print("\nARM B  REGISTRATION -- recover a planted similarity")
    ok_b = True
    for sc, rot, tx, ty in ((0.8826, 0.0, 40.0, -25.0), (1.05, 0.35, -60.0, 18.0)):
        th = np.deg2rad(rot)
        h, w = lum.shape
        R = np.array([[sc * np.cos(th), -sc * np.sin(th), tx],
                      [sc * np.sin(th), sc * np.cos(th), ty]])
        R[0, 2] += w / 2 - (R[0, 0] * w / 2 + R[0, 1] * h / 2)
        R[1, 2] += h / 2 - (R[1, 0] * w / 2 + R[1, 1] * h / 2)
        fake = cv2.warpAffine(lum, R.astype(np.float32), (w, h), flags=cv2.INTER_LINEAR)
        Ahat, diag = V.register(lum, fake)
        err = np.abs(Ahat - R)
        print("  planted scale %.4f rot %.2f deg t (%.0f,%.0f) -> recovered scale %.4f "
              "ecc %.4f inliers %d  max|dA| linear %.2e  shift %.2f px"
              % (sc, rot, tx, ty, diag["scale"], diag["ecc"], diag["inliers"],
                 err[:, :2].max(), err[:, 2].max()))
        ok_b = ok_b and err[:, :2].max() < 2e-3 and err[:, 2].max() < 4.0
    print("  ARM B %s" % ("PASS" if ok_b else "FAIL"))

    print("\nARM C  WARP BIAS -- the statistic through a real-sized geometry change")
    h, w = lum.shape
    for sc in (0.8826, 0.9570, 0.9974):
        S = np.array([[sc, 0.0, (1 - sc) * w / 2], [0.0, sc, (1 - sc) * h / 2]])
        shrunk = cv2.warpAffine(rgb, S.astype(np.float32), (w, h), flags=cv2.INTER_LINEAR)
        ww = V.warp_window(shrunk, S, y, x, WIN)
        r = V.blotch_ratio(V.lum_of(ww))[0]
        cw2 = V.warp_window(shrunk, S, cy, cx, CWIN)
        cc = V.gate_chroma(cw2, at=(0, 0))["chroma"]
        print("  cover %.4f  blotch %.6f (%.4fx)   chroma %.6f (%.4fx)"
              % (sc, r, r / b["contrast"], cc, cc / c["chroma"]))
    print("  ^ the round trip is a resample the real source arm also pays.")

    print("\nARM D  CONVICT -- blotch planted into the real master window")
    blk = V.lum_of(rgb)[y:y + WIN, x:x + WIN].copy()
    base = V.blotch_ratio(blk)
    sig = base[2]
    print("  window noise sigma %.1f DN, unplanted contrast %.5f" % (sig, base[0]))
    field = blot_field(blk.shape, rng)
    prev, ok_d = base[0], True
    for amp in (0.25, 0.5, 1.0, 2.0, 4.0):
        r = V.blotch_ratio(blk + field * amp * sig)[0]
        up = r > prev
        print("    amp %4.2f sigma  contrast %.5f  ratio vs unplanted %6.3fx  rises %s"
              % (amp, r, r / base[0], up))
        ok_d = ok_d and up
        prev = r
    print("  ARM D %s" % ("PASS" if ok_d else "FAIL"))

    print("\nARM E  CONVICT-CHROMA -- chroma mottle planted into the real chroma window")
    crop = rgb[cy:cy + CWIN, cx:cx + CWIN].astype(np.float64).copy()
    c0 = V.gate_chroma(crop.astype(np.float32), at=(0, 0))["chroma"]
    yy, xx = np.mgrid[0:CWIN, 0:CWIN].astype(np.float64)
    blob = np.sin(2 * np.pi * xx / 150.0) * np.sin(2 * np.pi * yy / 150.0)
    ylum = 0.299 * crop[..., 0] + 0.587 * crop[..., 1] + 0.114 * crop[..., 2]
    prev, ok_e = c0, True
    print("  unplanted chroma %.6f" % c0)
    for amp in (0.0005, 0.001, 0.002, 0.004, 0.008):
        img = crop.copy()
        img[..., 0] += ylum * amp * blob
        img[..., 2] -= ylum * amp * blob
        r = V.gate_chroma(img.astype(np.float32), at=(0, 0))["chroma"]
        up = r > prev
        print("    amp %.4f  chroma %.6f  ratio vs unplanted %6.3fx  rises %s"
              % (amp, r, r / c0, up))
        ok_e = ok_e and up
        prev = r
    print("  ARM E %s" % ("PASS" if ok_e else "FAIL"))

    print("\nCOMMISSIONED: %s" % ("YES" if (ok_a and ok_b and ok_d and ok_e) else "NO"))


if __name__ == "__main__":
    main()
