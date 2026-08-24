"""Is the 0.75 stops of unused headroom in the capture, or in strehl?

If the RAW's background sits at ~57% of the sensor's usable range, strehl is
being faithful and the capture is under-exposed. If the RAW is near its white
level and strehl still emits 57%, strehl has a scaling defect. These have
opposite fixes, so measure before touching anything.
"""
import glob
import os
import numpy as np
import rawpy

DIR = r"D:\personal\macro\bee-3-cpl"
files = sorted(glob.glob(os.path.join(DIR, "*.ARW")))
print("%d frames in %s" % (len(files), DIR))
pick = [files[0], files[len(files) // 2], files[-1]]

for p in pick:
    with rawpy.imread(p) as r:
        raw = r.raw_image_visible.astype(np.float64)
        black = np.mean(r.black_level_per_channel)
        white = float(r.white_level)
        cam = np.array(r.camera_whitebalance[:3], dtype=np.float64)
        colors = r.raw_colors_visible
        norm = (raw - black) / (white - black)
        h, w = norm.shape
        # Background patch: top-right, same region the render was measured in.
        patch = norm[:h // 6, -w // 6:]
        pc = colors[:h // 6, -w // 6:]
        g = patch[(pc == 1) | (pc == 3)]
        print()
        print(os.path.basename(p))
        print("  black %.1f  white %.0f  cam_wb %s" % (black, white, np.round(cam, 3)))
        qs = [float(np.percentile(norm, q)) for q in (50, 99, 99.9)]
        print("  whole frame  p50 %.4f  p99 %.4f  p99.9 %.4f  max %.4f"
              % (qs[0], qs[1], qs[2], float(norm.max())))
        print("  bg patch G   mean %.4f  p99.9 %.4f" % (g.mean(), np.percentile(g, 99.9)))
        print("  fraction of frame at >= 0.99 of white: %.6f%%"
              % (100.0 * (norm >= 0.99).mean()))
        wbg = g.mean() * (cam[1] / cam[1])
        print("  G after camera WB (G is the reference channel): %.4f" % wbg)
        print("  -> sRGB-encoded that lands near %.4f"
              % (wbg ** (1 / 2.2)))
