"""M41 step 9 -- the degenerate control, done properly.

a7_degenerate.py could NOT run the control section 8.4 specified.  It assumed
coffee-bubbles is at constant focus (fact 49).  MEASURED: on its detail ROI the
regularised focus response spans 3.60367 to 8.66036, a spread of 235.02 gate
sigma with a through-focus FWHM of 8 of 19 frames.  That is a strongly peaked
focus curve, not a flat one.  Whatever fact 49 means by "constant focus", the
shipped focus operator does not see it -- the subject itself changes between
frames.  So a7's D-vs-C residuals measure a real focus sweep and say nothing
about degeneracy.

The degenerate condition is therefore imposed directly instead of being hunted
for in the corpus: run the arms with s = 0, so every frame's OTF is identical by
construction.  The predictions are exact and can fail:

  * D'(s=0) must equal C to within the noise guard.  H = 1 for every frame, so
    the estimator is n*mean(Y)/(n + sigma^2/S) -- the mean, shrunk by a factor
    n/(n + sigma^2/S) that is within 1e-3 of 1 wherever S >> sigma^2/n.
  * D(s=0) must equal a single-image Wiener deconvolution of C by the measured
    diffraction OTF.  Its residual against C is a direct measurement of how much
    of arm D is the DIFFRACTION term with the focus axis switched off.
"""
import os, sys, glob, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m41lib as L
import m41lib2 as L2
from a2_run import load_two, core, oor, PAD
from a4_shipped_gate import fields

OUT = L.OUT


def main():
    with open(os.path.join(OUT, "rois_b.json")) as fh:
        rois = json.load(fh)
    log = open(os.path.join(OUT, "a9_degenerate.log"), "w", encoding="utf-8")

    def p(m):
        print(m); log.write(m + "\n"); log.flush()

    p("M41 step 9 -- degenerate control imposed by construction (s = 0).")
    for name in ("109MSDCF", "119MSDCF"):
        info = rois[name]
        for key in ("detail_roi", "flat_roi"):
            x, y, w, h = info[key]
            info[key] = [max(PAD, x), max(PAD, y), w, h]
        files = sorted(glob.glob(os.path.join(info["dir"], "*.ARW")))
        g, rn_e = info["g"], info["rn_e"]
        Dc, _ = load_two(files, tuple(info["detail_roi"]), tuple(info["detail_roi"]))
        _, reg = fields(Dc, g, rn_e)
        C = core(Dc.mean(0))
        scale = float(np.abs(C).mean())
        for lab, ud in (("D'(s=0) vs C  [EXACT-EQUALITY PREDICTION]", False),
                        ("D (s=0) vs C  [diffraction term alone]", True)):
            o = core(L2.arm_wiener2(Dc, reg, g, rn_e, 0.0, ud, True))
            d = o - C
            p(f"  [{name}] {lab}: RMS residual {np.sqrt((d*d).mean()):.4f} DN "
              f"({np.sqrt((d*d).mean())/scale*100:.4f}% of |C| = {scale:.1f} DN), "
              f"max |residual| {np.abs(d).max():.2f} DN, "
              f"out-of-range {oor(o, core(Dc))*100:.3f}%")
    log.close()


if __name__ == "__main__":
    main()
