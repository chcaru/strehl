r"""POSITIVE control for vc_score.py's paired path.

The identity selftest proves the scorer is quiet. It does not prove it can
respond. This plants a known radial CA of -508.4 ppm -- deliberately the exact
magnitude of the coefficient under test, eps_r = -508.4e-6 -- writes it as a
real TIFF, and requires the scorer to recover it through its shipped entry
point score(), not through an internal shortcut.
"""
import numpy as np, tifffile, os, sys
import vc_ca, vc_commission, vc_score

OLD = r"C:\dev\strehl-out\ORCH-FAITHFUL\faithful\%s.tiff"
SCRATCH = r"C:\dev\strehl-out\V-REVIEW"

subject = sys.argv[1]
plant_ppm = float(sys.argv[2]) if len(sys.argv) > 2 else -508.4
os.makedirs(SCRATCH, exist_ok=True)

img = vc_ca.load(OLD % subject)
H, W = img.shape[:2]
centre = (H/2.0, W/2.0)
out = vc_commission.plant_radial(img, 0, plant_ppm * 1e-6, centre)
tmp = os.path.join(SCRATCH, "positive-%s.tiff" % subject)
tifffile.imwrite(tmp, out)
print("wrote %s (%d bytes)" % (tmp, os.path.getsize(tmp)))

r = vc_score.score(subject, OLD % subject, tmp)
print("\nPOSITIVE control  subject=%s  planted %+0.1f ppm on R" % (subject, plant_ppm))
print("  n_paired    = %d" % r["n_paired"])
print("  ppmR_old    = %+.1f" % r["ppmR_old"])
print("  ppmR_new    = %+.1f" % r["ppmR_new"])
print("  delta       = %+.1f ppm   want %+.1f +/-20%%" % (r["d_ppmR"], plant_ppm))
print("  nsigma      = %.1f" % r["nsigma"])
print("  d_ppmB      = %+.1f ppm   want ~0 (blue untouched -- internal control)" % r["d_ppmB"])
print("  width_ratio = %.4f      want ~1 (resample, not blur)" % r["width_ratio"])
ok_r = abs(r["d_ppmR"] - plant_ppm) <= 0.20 * abs(plant_ppm)
ok_b = abs(r["d_ppmB"]) <= 40.0
ok_w = abs(r["width_ratio"] - 1.0) <= 0.05
print("\n  R recovery : %s" % ("ok" if ok_r else "*** FAIL ***"))
print("  B untouched: %s" % ("ok" if ok_b else "*** FAIL ***"))
print("  width null : %s" % ("ok" if ok_w else "*** FAIL ***"))
print("\n%s" % ("POSITIVE CONTROL PASSED" if (ok_r and ok_b and ok_w) else "*** POSITIVE CONTROL FAILED ***"))
os.remove(tmp)
print("removed %s" % tmp)
sys.exit(0 if (ok_r and ok_b and ok_w) else 1)
