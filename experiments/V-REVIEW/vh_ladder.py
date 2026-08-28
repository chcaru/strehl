"""CALIBRATION LADDER: plant a halo of KNOWN amplitude, then measure AND look.

Two questions the flagged verdicts cannot answer on their own:
  1. Does the instrument's "overshoot = N DN" actually correspond to N DN of
     planted rim? (calibration of the number against ground truth)
  2. What does N DN LOOK like at 1:1? (calibration of the number against the eye)

Host is a subject the instrument calls clean AND whose background is the most
uniform in the corpus (far-field sector spread 1100 DN), so the plant is not
competing with a scene gradient.

The rim is planted in the BACKGROUND only, as a Gaussian in distance from the
silhouette -- the same shape the instrument's near bands walk. Amplitudes
bracket flat-on-ruler-cpl's flagged +5680 DN.
"""
import os, subprocess, sys
import numpy as np
import tifffile
from scipy.ndimage import distance_transform_edt, label, zoom

sys.path.insert(0, r"C:\dev\blog\death-of-software\projects\strehl\experiments\ORCH-drift-check")
import halo_profile as H

HOST = "pencil-flatter-angle-cpl"
SRC = r"C:\dev\strehl-out\ORCH-FAITHFUL\faithful\%s.tiff" % HOST
OUT = r"D:\strehl-out\V-REVIEW\ladder"
AMPS = [0, 250, 500, 1000, 2000, 4500, 9000]
SIGMA = 14.0     # px, in full-res pixels
PEAK = 10.0      # distance from silhouette at which the rim peaks
SUB = 4

os.makedirs(OUT, exist_ok=True)
img = tifffile.imread(SRC)
print("host %s  shape=%s dtype=%s" % (HOST, img.shape, img.dtype))
y = H.luma(img)[::SUB, ::SUB]
t, subj = H.segment(y)
lab, n = label(subj)
dom = int(np.argmax(np.bincount(lab.ravel())[1:])) + 1
d, ind = distance_transform_edt(~subj, return_indices=True)
own = (lab[ind[0], ind[1]] == dom) & (~subj)
dfull_small = d * SUB

field = np.exp(-((dfull_small - PEAK) ** 2) / (2 * SIGMA ** 2)) * own
fy = zoom(field, (img.shape[0] / field.shape[0], img.shape[1] / field.shape[1]), order=1)
fy = np.clip(fy, 0, 1)[: img.shape[0], : img.shape[1]]
print("plant field: %d px above 0.5 (sub=4 grid), peak at d=%.0f px, sigma=%.0f"
      % (int((field > 0.5).sum()), PEAK, SIGMA))

rows = []
for a in AMPS:
    dst = os.path.join(OUT, "%s-A%05d.tiff" % (HOST, a))
    if a == 0:
        out = img.copy()
    else:
        add = (fy * a).astype(np.float32)
        out = img.astype(np.float32)
        for c in range(out.shape[2] if out.ndim == 3 else 1):
            out[:, :, c] += add
        out = np.clip(out, 0, 65535).astype(img.dtype)
    tifffile.imwrite(dst, out)
    clipped = float((out >= 65535).mean()) * 100
    v, over, bump, pen, farl, bands, why = H.profile(H.luma(out))
    rows.append((a, v, over, bump, clipped))
    print("planted %5d DN -> verdict %-12s overshoot %9s  bump %7s  clipped %.2f%%"
          % (a, v,
             ("%.1f" % over) if over is not None else "-",
             ("%.1f" % bump) if bump is not None else "-", clipped))

print("\n%-9s %-10s %-12s %-10s" % ("planted", "reported", "reported-base", "recovered"))
base = rows[0][2]
for a, v, over, bump, clip in rows:
    rec = (over - base) if over is not None and base is not None else None
    print("%-9d %-10s %-12s %-10s" % (
        a, ("%.1f" % over) if over is not None else "-",
        ("%.1f" % rec) if rec is not None else "-",
        ("%.2fx" % (rec / a)) if rec is not None and a else "-"))
