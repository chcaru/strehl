"""Two things:
(1) Reconcile ARM H1 (2.752 DN measured) with the derived ideal-step overshoot
    (11.79 DN).  Hypothesis: a single synthetic edge sits at ONE sub-pixel phase
    and the output grid need not sample the ringing peak.  Sweep the phase.
(2) Characterise what the kernel ADDS on real masters: lanczos - box."""
import sys, os, glob
import numpy as np
import tifffile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vh_hull as V

W, H = 7040, 350
print("== phase sweep: ONE edge, 12 sub-pixel phases, 160 DN step ==")
vals = []
for ph in range(12):
    a = np.zeros((H, W), np.float64)
    cut = W // 2 + ph            # slide the edge across one output pixel (5.03 px)
    a[:, :cut] = 40.0
    a[:, cut:] = 200.0
    a8 = np.clip(np.round(a), 0, 255).astype(np.uint8)
    hi, lo = V.hull_bounds(a8)
    out = V.reduce_f(a8, "lanczos")
    s = V.excess_stats(out, hi, lo)
    vals.append(max(s["max_excess"], s["max_deficit"]))
    print("   phase %2d/12  overshoot %6.3f DN" % (ph, vals[-1]))
print("   MEASURED range over phase: %.3f .. %.3f DN   (ARM H1 sampled %.3f)"
      % (min(vals), max(vals), vals[0]))
print("   DERIVED continuous ideal-step overshoot: 11.79 DN")
print("")

print("== what the kernel ADDS on real masters: lanczos - box ==")
print("%-38s %8s %8s %8s %8s %9s" % ("subject", "max+", "max-", "p99.99", "sd", "f>2DN"))
for pth in sorted(glob.glob(os.path.join(V.SHIP_V4, "*--SHIP-V4.tiff"))):
    subj = os.path.basename(pth).replace("--SHIP-V4.tiff", "")
    if subj not in ("lead-1-cpl", "109MSDCF", "tweezers-cpl", "lavendar-cpl",
                    "foam", "coffee-bubbles", "bee-1-cpl", "flowers-cpl"):
        continue
    a8 = V.to8(tifffile.imread(pth))
    d = np.zeros((0,))
    mx, mn, p9, sd, f2 = 0.0, 0.0, 0.0, 0.0, 0.0
    for c in range(3):
        lz = V.reduce_f(a8[:, :, c], "lanczos")
        bx = V.reduce_f(a8[:, :, c], "box")
        dd = lz - bx
        mx = max(mx, float(dd.max())); mn = min(mn, float(dd.min()))
        p9 = max(p9, float(np.percentile(np.abs(dd), 99.99)))
        sd = max(sd, float(dd.std()))
        f2 = max(f2, float((np.abs(dd) > 2.0).mean()))
    print("%-38s %8.2f %8.2f %8.2f %8.3f %9.5f" % (subj, mx, mn, p9, sd, f2))
