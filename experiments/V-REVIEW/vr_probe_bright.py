import os, sys
import numpy as np, tifffile, cv2, rawpy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vr_lib as V

subj = sys.argv[1] if len(sys.argv) > 1 else "foam"
paths = [("master", V.master_path(subj))]
for k in (0, 50):
    q = os.path.join(V.OUT, "%s--f%04d.tiff" % (subj, k))
    if os.path.exists(q):
        paths.append(("frame%d" % k, q))
for nm, q in paths:
    a = tifffile.imread(q)[:, :, :3].astype(np.float32)
    l = V.lum_of(a)
    print("%-8s mean %8.1f  p1 %7.1f p50 %8.1f p99 %8.1f  frac>60000 %.4f" %
          (nm, l.mean(), *np.percentile(l, [1, 50, 99]), float((l > 60000).mean())))
    th = cv2.resize(a, (879, 586), interpolation=cv2.INTER_AREA)
    th = np.clip(th / 65535.0 * 255, 0, 255).astype(np.uint8)
    cv2.imwrite(os.path.join(V.OUT, "thumb-%s-%s.png" % (subj, nm)), th[:, :, ::-1])
    del a, l
frames = V.frames_of(subj)
print("\nraw level check (rawpy raw_image mean, no processing):")
for k in (0, 1, 25, 50, 75, 99):
    if k < len(frames):
        with rawpy.imread(frames[k]) as r:
            m = float(r.raw_image_visible.mean())
        print("  frame %3d %-28s raw mean %8.1f" % (k, os.path.basename(frames[k]), m))
