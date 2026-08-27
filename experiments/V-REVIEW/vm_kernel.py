"""Does the stacker's own gather kernel inject rims?
All arms share alignment, photometry, merge and raster, so those terms cancel.
nearest and bilinear have NO negative lobes; catmull-rom (SHIPPING DEFAULT) and
lanczos3 do.

Statistic: excess(X vs REF) = max(0, X - dilate(REF, r)).  Positive means X is
brighter than anything REF produced within r px.

THE REFERENCE TERM IS COMMISSIONED, not assumed: nearest-vs-bilinear are both
non-ringing, so whatever excess THEY show is the sharpness floor of the
statistic.  A ringing verdict must clear that floor, not merely exceed zero."""
import os
import numpy as np, cv2, tifffile

ROOT = r"C:\dev\strehl-out\V-REVIEW\merge"
arms = {}
for r in ("nearest", "bilinear", "catmull-rom", "lanczos3"):
    arms[r] = tifffile.imread(os.path.join(ROOT, "arm2-%s.tiff" % r)).astype(np.float32)

def exc(x, ref, r):
    k = np.ones((2 * r + 1, 2 * r + 1), np.uint8)
    out = 0.0
    stats = []
    for c in range(3):
        d = cv2.dilate(ref[:, :, c], k)
        e = np.maximum(x[:, :, c] - d, 0.0)
        stats.append(e)
    e = np.maximum(np.maximum(stats[0], stats[1]), stats[2])
    return e

REF = "bilinear"
print("reference arm: %s   (no negative lobes)" % REF)
print("%-26s %10s %10s %10s %12s" % ("arm vs reference", "max DN", "p99.99", "p99.9", "frac>50DN"))
res = {}
for r in ("bilinear", "nearest", "catmull-rom", "lanczos3"):
    for rad in (2,):
        e = exc(arms[r], arms[REF], rad)
        res[r] = e
        print("%-26s %10.1f %10.1f %10.1f %12.6f"
              % ("%s vs %s (r=%d)" % (r, REF, rad), e.max(),
                 np.percentile(e, 99.99), np.percentile(e, 99.9), (e > 50).mean()))
print("")
print("CONTROLS")
print("  identity (bilinear vs itself) max %.3f DN  -- must be 0" % res["bilinear"].max())
print("  sharpness floor (nearest, non-ringing) p99.99 = %.1f DN" % np.percentile(res["nearest"], 99.99))
print("  catmull-rom p99.99 = %.1f DN   ratio vs floor %.2fx"
      % (np.percentile(res["catmull-rom"], 99.99),
         np.percentile(res["catmull-rom"], 99.99) / max(np.percentile(res["nearest"], 99.99), 1e-9)))
print("  lanczos3    p99.99 = %.1f DN   ratio vs floor %.2fx"
      % (np.percentile(res["lanczos3"], 99.99),
         np.percentile(res["lanczos3"], 99.99) / max(np.percentile(res["nearest"], 99.99), 1e-9)))
mx = float(np.percentile(arms[REF][:, :, 1], 99.9))
print("")
print("  scale: reference arm p99.9 level = %.0f DN (16-bit linear)" % mx)
print("  catmull-rom excess p99.99 as %% of that level: %.3f%%"
      % (100.0 * np.percentile(res["catmull-rom"], 99.99) / mx))
