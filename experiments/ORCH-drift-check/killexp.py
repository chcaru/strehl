"""Try to kill fact 1257.

Two confounds could inflate the headroom numbers:

  C1. rawpy reports white_level = 16383 for Sony ARW, but the true saturation
      point of the sensor may be LOWER at some ISOs. If so, every frame is
      closer to clipping than I computed, and the headroom shrinks.
      TEST: on a stack that demonstrably clips (dry-erase-marker-head-cpl,
      3.67% at >=0.99), the observed maximum raw value IS the true saturation
      point. Compare it to the reported white_level. If they agree, C1 is dead.

  C2. p99.9 discards the top 33k pixels of a 33 MP frame. If the choice of
      percentile drives the verdict, the number is an artifact of the
      statistic rather than of the exposure.
      TEST: recompute headroom at p99, p99.9, p99.99 and p100 and report the
      spread.

  C3. p99.9 is taken over all CFA positions at once. Without white balance
      green reads ~2.6x higher than red, so the all-pixel percentile should
      track green. Confirm that green really is the limiting channel, since
      it is green that clips first and therefore green that caps exposure.

READ-ONLY on D:\\.
"""
import glob
import os
import numpy as np
import rawpy

ROOT = r"D:\personal\macro"

CLIPPER = "dry-erase-marker-head-cpl"   # 3.6726% at >=0.99 -- it saturates
DARK = "bee-3-cpl"                      # +1.69 stops claimed
DARKEST = "lead-1-cpl"                  # +4.39 stops claimed

print("=" * 78)
print("C1. Is the reported white_level the true saturation point?")
print("=" * 78)
print("%-30s %8s %8s %8s %9s" % ("stack", "white", "obs max", "black", "frames"))
for name in (CLIPPER, DARK, DARKEST):
    files = sorted(glob.glob(os.path.join(ROOT, name, "*.ARW")))
    pick = files[:: max(1, len(files) // 5)][:5]
    mx, wl, bl = 0, None, None
    for p in pick:
        with rawpy.imread(p) as r:
            mx = max(mx, int(r.raw_image_visible.max()))
            wl = int(r.white_level)
            bl = float(np.mean(r.black_level_per_channel))
    print("%-30s %8d %8d %8.1f %9d" % (name, wl, mx, bl, len(pick)))

print()
print("A stack that clips must reach the true saturation point. If its")
print("observed max is well below the reported white_level, the reported")
print("white_level is wrong and every headroom number is inflated by")
print("log2(white/true_sat).")

print()
print("=" * 78)
print("C2 + C3. Percentile choice, and which CFA channel limits exposure")
print("=" * 78)

for name in (CLIPPER, DARK, DARKEST):
    files = sorted(glob.glob(os.path.join(ROOT, name, "*.ARW")))
    p = files[len(files) // 2]
    with rawpy.imread(p) as r:
        raw = r.raw_image_visible.astype(np.float32)
        black = float(np.mean(r.black_level_per_channel))
        white = float(r.white_level)
        norm = (raw - black) / (white - black)
        colors = r.raw_colors_visible
    print()
    print("%s  (%s)" % (name, os.path.basename(p)))
    print("  %-10s %9s %9s %9s %9s" % ("channel", "p99", "p99.9", "p99.99", "max"))
    for label, sel in (("all", np.ones_like(colors, bool)),
                       ("R", colors == 0),
                       ("G", (colors == 1) | (colors == 3)),
                       ("B", colors == 2)):
        v = norm[sel]
        q = [np.percentile(v, 99), np.percentile(v, 99.9),
             np.percentile(v, 99.99), v.max()]
        print("  %-10s %9.4f %9.4f %9.4f %9.4f"
              % (label, q[0], q[1], q[2], q[3]))
    print("  headroom (stops) from each statistic, all-pixel:")
    v = norm.ravel()
    for lbl, val in (("p99", np.percentile(v, 99)),
                     ("p99.9", np.percentile(v, 99.9)),
                     ("p99.99", np.percentile(v, 99.99)),
                     ("max", v.max())):
        print("    %-8s %+6.2f" % (lbl, -np.log2(max(float(val), 1e-6))))
