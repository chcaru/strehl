"""M41 step 7 -- DEGENERATE CONTROL on coffee-bubbles (19 frames, CONSTANT focus,
fact 49).

Section 8.4 pre-registered this as "D must equal C".  That prediction is only
half right and the script says so BEFORE reporting the numbers.  With every
frame at the same focus every H_k is identical, so

    D = sum_k H* Y_k / (n|H|^2 + sigma^2/S) = mean(Y) * n H* / (n|H|^2 + sigma^2/S)

which is the MEAN followed by a single-image Wiener deconvolution by H.  So:
  * arm D'  (no diffraction term, H = 1) must equal arm C to within the guard,
    and that IS an exact-equality prediction that can fail;
  * arm D   (with the measured diffraction OTF) must equal a Wiener-deconvolved
    C, not C itself.  Its residual against C is a MEASUREMENT of how much the
    diffraction term alone is doing, with the focus axis removed.

Read-only corpus; nothing is written to D:\\.
"""
import os, sys, glob, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m41lib as L
import m41lib2 as L2
from a2_run import load_two, core, oor, PAD
from a4_shipped_gate import fields, arm_A_shipped, solve_gate

OUT = L.OUT


def rel(a, b):
    d = a - b
    return float(np.sqrt((d * d).mean())), float(np.abs(d).max()), float(np.abs(b).mean())


def main():
    with open(os.path.join(OUT, "rois_b.json")) as fh:
        rois = json.load(fh)
    info = rois["coffee-bubbles"]
    for key in ("detail_roi", "flat_roi"):
        x, y, w, h = info[key]
        info[key] = [max(PAD, x), max(PAD, y), w, h]
    files = sorted(glob.glob(os.path.join(info["dir"], "*.ARW")))
    g, rn_e = info["g"], info["rn_e"]
    log = open(os.path.join(OUT, "a7_degenerate.log"), "w", encoding="utf-8")

    def p(m):
        print(m); log.write(m + "\n"); log.flush()

    Dc, Fc = load_two(files, tuple(info["detail_roi"]), tuple(info["flat_roi"]))
    _, reg = fields(Dc, g, rn_e)
    curve = reg.reshape(len(files), -1).mean(1)
    p(f"coffee-bubbles: {len(files)} frames ISO {info['iso']}, detail ROI "
      f"{info['detail_roi']}")
    p(f"  through-focus response across frames: min {curve.min():.5f} "
      f"max {curve.max():.5f} spread {(curve.max()-curve.min()):.5f} = "
      f"{(curve.max()-curve.min())/(np.sqrt(2)*0.015214):.2f} gate sigma")
    p("  (fact 49 says this stack is at CONSTANT focus; the spread above is the "
      "check that it really is, in the shipped gate's own units)")

    s, fwm, fwd = L.calibrate_s(core(Dc), core(reg), g, rn_e, True)
    p(f"  self-calibrated s = {s:.4f} quad px/frame (FWHM measured {fwm:.1f} of "
      f"{len(files)} frames -> a flat curve should saturate the frame count)")

    C = core(Dc.mean(0))
    for lab, use_diff in (("D'", False), ("D", True)):
        out = core(L2.arm_wiener2(Dc, reg, g, rn_e, s, use_diff, True))
        r, mx, scale = rel(out, C)
        p(f"  {lab} vs C: RMS residual {r:.4f} DN, max |residual| {mx:.2f} DN, "
          f"relative RMS {r/max(scale,1e-9)*100:.4f}% of |C|; "
          f"out-of-range {oor(out, core(Dc))*100:.3f}%")
    log.close()


if __name__ == "__main__":
    main()
