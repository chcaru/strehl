"""(1) Is the provably-manufactured excess AT EDGES?  (character of the halo)
(2) Robustness: does the hull bound depend on my chosen support / coordinate map?
    If the mapping were offset, the sign-matched worst case would fall short."""
import sys, os
import numpy as np, cv2, tifffile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vh_hull as V

SUBJ = ["lead-1-cpl", "109MSDCF", "tweezers-cpl", "lavendar-cpl", "foam", "flowers-cpl"]

print("== support sensitivity of the hull bound (lead-1-cpl, green) ==")
a8 = V.to8(tifffile.imread(os.path.join(V.SHIP_V4, "lead-1-cpl--SHIP-V4.tiff")))[:, :, 1]
for sup in (16, 18, 24, 32):
    hi, lo = V.hull_bounds(a8, support=sup)
    r = {}
    for k in ("box", "lanczos"):
        s = V.excess_stats(V.reduce_f(a8, k), hi, lo)
        r[k] = (s["max_excess"], s["max_deficit"])
    print("   support %2d px : box %.4f/%.4f   lanczos %7.3f/%7.3f"
          % (sup, r["box"][0], r["box"][1], r["lanczos"][0], r["lanczos"][1]))
print("   (box must stay 0 and lanczos must be stable, or my coordinate map is wrong)")
print("")

print("== is the manufactured excess at EDGES? ==")
print("%-16s %10s %10s %10s   %s" % ("subject", "grad@exc", "grad@all", "ratio", "verdict"))
for subj in SUBJ:
    a8f = V.to8(tifffile.imread(os.path.join(V.SHIP_V4, subj + "--SHIP-V4.tiff")))
    worst = None
    for c in range(3):
        p = a8f[:, :, c]
        hi, lo = V.hull_bounds(p)
        out = V.reduce_f(p, "lanczos")
        exc = np.maximum(np.maximum(out - hi, 0.0), np.maximum(lo - out, 0.0))
        bx = V.reduce_f(p, "box")
        gx = cv2.Sobel(bx, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(bx, cv2.CV_32F, 0, 1, ksize=3)
        g = cv2.magnitude(gx, gy)
        m = exc > 2.0
        if m.sum() < 50:
            continue
        ge, ga = float(g[m].mean()), float(g.mean())
        if worst is None or ge / max(ga, 1e-6) > worst[2]:
            worst = (ge, ga, ge / max(ga, 1e-6), int(m.sum()))
    if worst is None:
        print("%-16s %10s %10s %10s   too few excess px (<50)" % (subj, "-", "-", "-"))
    else:
        print("%-16s %10.1f %10.1f %10.2fx  %d px above 2 DN"
              % (subj, worst[0], worst[1], worst[2], worst[3]))
