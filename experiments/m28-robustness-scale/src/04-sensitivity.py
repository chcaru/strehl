"""
M28 / 04 -- How big does an outlier have to be before the mask sees it?

Scripts 01-03 established a baseline; they did not establish sensitivity. A
detector whose baseline sits at the noise floor is worthless if nothing real
clears it. This plants a known outlier of known size and measures the detection
rate against a false-positive rate calibrated on the same stack.

THE DETECTOR, corrected by script 02. R10 as written compares each frame against
a running estimate over the whole stack. Script 02 measured that the pairwise
noise-normalised residual on the CLEAN stack grows nearly linearly with frame
separation -- 1.13 at dk=1 to 12.30 at dk=16, a 10.9x rise over a 16x separation
-- which is the signature of an accumulating geometric warp, not of noise
(flat) and not of defocus (which saturates once a region is fully blurred). So a
whole-stack reference buys about 10x more geometric residual than an adjacent
one for no gain. This detector therefore uses the IMMEDIATE NEIGHBOURS:

    z_k = |a_k - (a_{k-1} + a_{k+1})/2| / (sigma * sqrt(1.5))

THE PLANT. A W x W tile of frame k0 is replaced by the same tile taken s pixels
away IN THE SAME FRAME. Noise statistics, defocus level, illumination and
sensor position are therefore all correct by construction -- the only thing that
changed is that the content moved, which is exactly the failure a robustness
mask exists to catch. Facts 61-64 exist because this project has shipped bad
plants before; the guard here is that nothing is synthesised.

THE PLACEBO is s = 0: the identical copy. It exercises every line of the
planting machinery and must produce zero detections. If it does not, the
detector is measuring the plant apparatus.

PRE-REGISTERED PREDICTIONS:

  P10  The s=0 placebo detects at exactly the false-positive rate.
  P11  Detection is monotone in s.
  P12  The threshold shift is ~1 pixel of the DECIMATED grid, i.e. s ~ D, since
       below that the tile still overlaps itself almost entirely.
  P13  At dk=1 the residual has no radial trend, because one frame of breathing
       displaces the corner by well under a pixel -- the clean complement to
       script 02's finding at dk=16.
"""
import os, json
import numpy as np

BLACK, CROP = 512.0, 3072
CACHE = os.path.join(os.path.dirname(__file__), "..", "out", "cache")
HOST, ISO = "109MSDCF", 160.0
W = 128                       # plant tile, green-sublattice pixels
SHIFTS = [0, 1, 2, 4, 8, 16, 32]
SCALES = [4, 8, 16]


def noise_params(iso):
    g = iso / 436.8
    return g, ((4.20 if iso < 400 else 1.47) * g) ** 2


def area_mean(a, d):
    n, h, w = a.shape
    h2, w2 = (h // d) * d, (w // d) * d
    return a[:, :h2, :w2].reshape(n, h2 // d, d, w2 // d, d).mean(axis=(2, 4))


def neighbour_z(a, g, rn2, d):
    ref = (a[:-2] + a[2:]) / 2.0
    sig = np.sqrt(np.maximum(g * np.maximum(ref, 0) + rn2, 1e-6)) / d
    return np.abs(a[1:-1] - ref) / (sig * np.sqrt(1.5))


raw = np.load(os.path.join(CACHE, f"{HOST}.npy"))
n = len(raw)
g, rn2 = noise_params(ISO)
gain = raw.reshape(n, -1).mean(axis=1)            # script 03: mean, not median
gain = gain / np.median(gain)
raw = raw / gain[:, None, None]
H = raw.shape[1]
k0 = n // 2
print(f"host {HOST}: {n} frames, {H}x{H} green px, planting into frame {k0}")

# ---- P13: is the dk=1 residual radially flat? -------------------------------
d = 8
a = area_mean(raw, d)
z1 = np.median(neighbour_z(a, g, rn2, d), axis=0)
h = z1.shape[0]
yy, xx = np.mgrid[0:h, 0:h]
r = np.sqrt((yy - (h - 1) / 2.) ** 2 + (xx - (h - 1) / 2.) ** 2)
edges = np.linspace(0, r.max(), 9)
prof = [float(np.median(z1[(r >= edges[i]) & (r < edges[i + 1])])) for i in range(8)]
print("\nP13  radial |z| at adjacent-frame reference, d=8:")
print("     " + " ".join(f"{v:6.2f}" for v in prof))
print(f"     outer/inner {prof[-1]/prof[0]:5.2f}   (script 02 saw 1.82 with a "
      f"whole-stack reference)")

# ---- tile grid ---------------------------------------------------------------
nt = H // W
origins = [(iy * W, ix * W) for iy in range(nt) for ix in range(nt)
           if iy * W + W + max(SHIFTS) <= H and ix * W + W <= H]
print(f"\n{len(origins)} plantable {W}x{W} tiles")

results = {}
for d in SCALES:
    base_z = neighbour_z(area_mean(raw, d), g, rn2, d)
    kk = k0 - 1                                    # index into the trimmed stack
    tb = d and W // d
    # Null distribution: the SAME tiles in the SAME frame, unplanted.
    null = np.array([np.median(base_z[kk, y // d:y // d + tb, x // d:x // d + tb])
                     for (y, x) in origins])
    # False-positive calibration uses every OTHER frame's tiles, so the null and
    # the threshold are not the same numbers.
    others = np.array([np.median(base_z[k, y // d:y // d + tb, x // d:x // d + tb])
                       for k in range(base_z.shape[0]) if k != kk
                       for (y, x) in origins])
    thr = {p: float(np.percentile(others, 100 - p)) for p in (5.0, 1.0, 0.1)}
    row = {"thr": thr, "null_med": float(np.median(null)), "det": {}}
    print(f"\n--- scale d={d}  tile {tb}x{tb}  thresholds "
          + "  ".join(f"FPR{p}%={t:.2f}" for p, t in thr.items()))
    for s in SHIFTS:
        pl = raw.copy()
        for (y, x) in origins:
            pl[k0, y:y + W, x:x + W] = raw[k0, y + s:y + s + W, x:x + W]
        zz = neighbour_z(area_mean(pl, d), g, rn2, d)
        tile = np.array([np.median(zz[kk, y // d:y // d + tb, x // d:x // d + tb])
                         for (y, x) in origins])
        det = {p: float((tile > t).mean()) for p, t in thr.items()}
        row["det"][s] = {"median_z": float(np.median(tile)), "rate": det}
        print(f"    shift {s:3d} px   median tile |z| {np.median(tile):7.2f}   "
              + "  ".join(f"det@FPR{p}% {100*v:6.1f}%" for p, v in det.items())
              + ("   <-- PLACEBO" if s == 0 else ""))
        del pl, zz
    results[d] = row

with open(os.path.join(os.path.dirname(__file__), "..", "out",
                       "04-sensitivity.json"), "w") as fh:
    json.dump({"radial_dk1": prof, "scales": {str(k): v for k, v in results.items()}},
              fh, indent=1)
print("\nP10: placebo must detect at the FPR and no higher.")
print("P12: predicted threshold shift ~ d px.")
