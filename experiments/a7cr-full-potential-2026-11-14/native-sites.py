"""Check `STREHL_CARRY_RGB` against the plain render: at every pixel the
channel native to its CFA site (RGGB: red at even-even, green at the two mixed
sites, blue at odd-odd) must be identical, because the carry folds the same
four CFA planes on the same election and only adds the other channels. The
non-native channels are where the two may differ; their difference is
reported as a size, not a pass/fail.

  python -X utf8 native-sites.py CARRY.tif PLAIN.tif

Fooled by: nothing that makes the native channels agree by accident; a
carry that wrote nothing at all would differ in the non-native channels by
zero, which the second line shows.
"""
import sys

import numpy as np
import tifffile

a = tifffile.imread(sys.argv[1]).astype(np.int32)
b = tifffile.imread(sys.argv[2]).astype(np.int32)
assert a.shape == b.shape, (a.shape, b.shape)
h, w, _ = a.shape
native = np.zeros((h, w), dtype=np.int64)
native[0::2, 1::2] = 1
native[1::2, 0::2] = 1
native[1::2, 1::2] = 2
idx = native[..., None] == np.arange(3)[None, None, :]
d = np.abs(a - b)
print(f'native channel: {int((d[idx] != 0).sum())} of {int(idx.sum())} samples differ, max {int(d[idx].max())}')
nn = d[~idx]
print(f'non-native channels: {100 * float((nn != 0).mean()):.1f}% differ, mean |diff| {float(nn.mean()):.1f}, '
      f'p99 {float(np.percentile(nn, 99)):.0f} DN of 65535')
