"""M126: locate where a treatment actually acted.

Used to FIND the treated region, not to rank arms. ORCH's warning about
max-disagreement crops applies to ranking; locating where a switch did its
work is exactly what a difference map is for.

Reports the 512-block with the largest mean |difference| between two arms.
"""
import sys
import numpy as np
import tifffile  # hard import -- no PIL fallback

TAG, A_ARM, B_ARM = sys.argv[1], sys.argv[2], sys.argv[3]
ROOT = rf"C:\dev\strehl-out\M126-COMPOSITE\{TAG}"
S = 512


def load(p):
    a = tifffile.imread(p)
    assert a.dtype == np.uint16, f"{p}: dtype {a.dtype}, expected uint16"
    return a


a = load(rf"{ROOT}\lin\{A_ARM}.tif").astype(np.int32)
b = load(rf"{ROOT}\lin\{B_ARM}.tif").astype(np.int32)
d = np.abs(a - b).mean(axis=2)
h, w = d.shape
print(f"{B_ARM} vs {A_ARM}: {(d != 0).mean() * 100:.3f}% of pixels differ, "
      f"peak {d.max() / 65535 * 100:.3f}% FS, mean {d.mean():.2f} DN")

best = []
for y in range(0, h - S, S // 2):
    for x in range(0, w - S, S // 2):
        best.append((float(d[y:y + S, x:x + S].mean()), x, y))
best.sort(reverse=True)
print(f"\ntop 5 blocks by mean |diff| ({B_ARM} vs {A_ARM}):")
for m, x, y in best[:5]:
    print(f"  ({x:5d},{y:5d})  mean |diff| = {m:8.2f} DN")
