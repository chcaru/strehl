"""Coarse green-luma reference from a merged sensor master, for the
consistency-gate experiment (`STREHL_COARSE_REFERENCE`).

usage: coarse-reference.py SENSOR_MASTER.tif OUT.f32 [levels=2]

The sensor master holds the merge's compact R/G1/G2/B planes (black-subtracted
raw DN, analysis domain). Luma is (G1+G2)/2, the plane the merge selects on;
it is reduced `levels` times with the pyramid's own REDUCE (binomial
[1,4,6,4,1]/16, clamped taps at 2c+t-2, ceil sizes). Prints width and height.
"""
import sys
import numpy as np
import tifffile

K = np.array([1, 4, 6, 4, 1], np.float64) / 16.0


def reduce_axis(a, axis):
    n = a.shape[axis]
    m = (n + 1) // 2
    idx = np.clip(2 * np.arange(m)[:, None] + np.arange(5)[None, :] - 2, 0, n - 1)
    taken = np.take(a, idx, axis=axis)  # shape with (m,5) at axis
    return np.tensordot(taken, K, axes=([axis + 1], [0])) if axis == 0 else np.tensordot(taken, K, axes=([axis + 1], [0]))


def reduce2d(a):
    return reduce_axis(reduce_axis(a, 1), 0)


m = tifffile.imread(sys.argv[1]).astype(np.float64)
levels = int(sys.argv[3]) if len(sys.argv) > 3 else 2
if m.ndim == 3 and m.shape[-1] == 4:
    luma = 0.5 * (m[..., 1] + m[..., 2])
elif m.ndim == 3 and m.shape[0] == 4:
    luma = 0.5 * (m[1] + m[2])
else:  # RGGB mosaic
    luma = 0.5 * (m[0::2, 1::2] + m[1::2, 0::2])
for _ in range(levels):
    luma = reduce2d(luma)
luma.astype("<f4").tofile(sys.argv[2])
print(f"{luma.shape[1]},{luma.shape[0]}")
