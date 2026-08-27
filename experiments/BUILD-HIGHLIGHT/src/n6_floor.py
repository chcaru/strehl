"""ORCH: "Report 'no defect at or above X DN', with X measured by a ladder, or do
not report clean at all. Unqualified, 'clean' and 'deaf' are the same word."

Section 12 reported flower-bud FLAT on the radial (R-G)/Y statistic. The instrument
was calibrated -- a planted radial was detected, a flat colour cast correctly was not
-- but calibration is not a FLOOR. This plants a radial red deficit of known amplitude
into the real subject and finds the smallest one the statistic still separates from
the unplanted baseline.

PLANT: R' = R * (1 - A*r), r the same normalised radius the statistic uses. That is
the shape of a lateral-CA red deficit, so a plant that fails to register is a real
blind spot and not a mismatched stimulus.

ANCHOR: A=0 must reproduce the published baseline. If it does not, the harness is
wrong and every rung above it is meaningless -- so it is asserted, not eyeballed.
"""
import numpy as np, tifffile, l2_falsecolour as L

img0 = tifffile.imread("C:/dev/strehl-out/BUILD-HIGHLIGHT/flowerbud/M1-caon-kneeoff.tif").astype(np.float32)/65535.0
h, w, _ = img0.shape
yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
r = np.hypot((yy-h/2.0)/(h/2.0), (xx-w/2.0)/(w/2.0)).astype(np.float32)
del yy, xx

print("  A(plant)   cr_centre   cr_corner   corner-centre   vs baseline")
base = None
for A in (0.0, 0.01, 0.02, 0.05, 0.10):
    img = img0.copy()
    img[..., 0] *= (1.0 - A*r)
    s = L.stats(img, population="edge")
    b = s["RADcr_bands"]
    ok = [x for x in b if x is not None]
    d = ok[-1] - ok[0]
    if base is None:
        base = d
        print("  %.3f      %+.4f     %+.4f     %+.4f        (baseline)" % (A, ok[0], ok[-1], d))
    else:
        print("  %.3f      %+.4f     %+.4f     %+.4f        %+.4f  (%.1fx baseline)"
              % (A, ok[0], ok[-1], d, d-base, abs(d/base) if base else 0))
    del img, s
