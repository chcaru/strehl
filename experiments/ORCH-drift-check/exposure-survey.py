"""Survey exposure across every macro stack the owner has delivered.

If the 1.76-stop shortfall on bee-3-cpl is systematic, it is the single
largest quality lever available to this project, and it costs nothing but a
change in capture: 1.76 stops is 3.4x the photons, which is 1.85x less shot
noise before the stacker does anything at all.

Reads two frames per directory. READ-ONLY: nothing is written to D:\\.
"""
import glob
import os
import numpy as np
import rawpy

ROOT = r"D:\personal\macro"
dirs = sorted(d for d in glob.glob(os.path.join(ROOT, "*"))
              if os.path.isdir(d))
print("%-34s %5s %7s %8s %8s %9s" %
      ("stack", "n", "hdroom", "bg", "p99.9", "clipped%"))
print("-" * 80)

rows = []
for d in dirs:
    files = sorted(glob.glob(os.path.join(d, "*.ARW")))
    if not files:
        continue
    pick = [files[0]] if len(files) < 4 else [files[0], files[len(files) // 2]]
    best = []
    for p in pick:
        try:
            with rawpy.imread(p) as r:
                raw = r.raw_image_visible.astype(np.float32)
                black = float(np.mean(r.black_level_per_channel))
                white = float(r.white_level)
                norm = (raw - black) / (white - black)
                p999 = float(np.percentile(norm, 99.9))
                h, w = norm.shape
                colors = r.raw_colors_visible
                tr = norm[:h // 8, -w // 8:]
                tc = colors[:h // 8, -w // 8:]
                bgv = float(np.median(tr[(tc == 1) | (tc == 3)]))
                clip = float((norm >= 0.99).mean())
                best.append((p999, bgv, clip))
        except Exception as e:
            print("%-34s  ERROR %s" % (os.path.basename(d), e))
            break
    if not best:
        continue
    p999 = max(b[0] for b in best)
    bgv = float(np.mean([b[1] for b in best]))
    clip = max(b[2] for b in best)
    head = -np.log2(max(p999, 1e-6))
    rows.append((os.path.basename(d), len(files), head, bgv, p999, clip))
    print("%-34s %5d %+6.2f  %7.4f %8.4f %8.4f%%"
          % (os.path.basename(d), len(files), head, bgv, p999, 100 * clip))

if rows:
    heads = np.array([r[2] for r in rows])
    print("-" * 80)
    print("stacks surveyed: %d" % len(rows))
    print("unused headroom: median %+.2f stops, min %+.2f, max %+.2f"
          % (float(np.median(heads)), float(heads.min()), float(heads.max())))
    under = int((heads > 0.5).sum())
    print("%d of %d stacks leave more than half a stop on the table"
          % (under, len(rows)))
    med = float(np.median(heads))
    print()
    print("recovering the median %+.2f stops would collect %.2fx the photons,"
          % (med, 2 ** med))
    print("which is %.2fx less shot noise before any stacking." % (2 ** (med / 2)))
