r"""Positive control on the empty defect map: measure the query's reach.

`dustmap.py` found 0 sites at (excess>48DN, hit in >=90% of darks) and an
absence result is a statement about the query until the query's reach is
measured. This sweeps the threshold and reports the excess distribution, so the
empty result can be read as either "this sensor is clean" or "this threshold is
unreachable" rather than being ambiguous between them -- the same lexical-vs-
physical failure that made an earlier build audit report NOT FOUND for a binary
that was present under a different filename.
"""
import glob
import numpy as np
import rawpy
from scipy import ndimage

dk = sorted(glob.glob(r"D:\macro-dark-frames\**\*.ARW", recursive=True))
use = dk[::5][:24]
print("darks used:", len(use))
THR = [4, 8, 16, 32, 48]
hits = None
mx = None
for i, f in enumerate(use):
    with rawpy.imread(f) as r:
        a = r.raw_image_visible.astype(np.float32)
    if hits is None:
        hits = {t: np.zeros(a.shape, np.int16) for t in THR}
        mx = np.zeros(a.shape, np.float32)
    for dy in (0, 1):
        for dx in (0, 1):
            pl = a[dy::2, dx::2]
            ex = pl - ndimage.median_filter(pl, size=3, mode="nearest")
            for t in THR:
                hits[t][dy::2, dx::2] += (ex > t).astype(np.int16)
            np.maximum(mx[dy::2, dx::2], ex, out=mx[dy::2, dx::2])
    if i == 0:
        print("frame0 excess percentiles 99/99.9/99.99/max: %.1f %.1f %.1f %.1f"
              % tuple(np.percentile(ex, [99, 99.9, 99.99]).tolist() + [ex.max()]))
        print("frame0 raw min/median/max: %.0f %.0f %.0f"
              % (a.min(), np.median(a), a.max()))
n = len(use)
print("\nmax-over-darks excess percentiles: 99.9%%=%.1f 99.99%%=%.1f max=%.1f"
      % (np.percentile(mx, 99.9), np.percentile(mx, 99.99), mx.max()))
print("\nthr   sites hitting in >=n darks")
print("      %s" % "  ".join("%4d" % k for k in (n, int(.9*n), int(.75*n), int(.5*n), 2)))
for t in THR:
    h = hits[t]
    print("%4d  %s" % (t, "  ".join("%4d" % int((h >= k).sum())
                                    for k in (n, int(.9*n), int(.75*n), int(.5*n), 2))))
