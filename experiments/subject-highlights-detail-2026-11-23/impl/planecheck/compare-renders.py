"""Compare two renders' pixels, and say how their TIFFs differ otherwise.

  python compare-renders.py <a.tiff> <b.tiff>

Prints: shape and dtype, whether the pixel arrays are identical, and if not the share of
pixels that differ and the largest difference; then the TIFF tags whose values differ.
"""
import sys

import numpy as np
import tifffile

a_path, b_path = sys.argv[1], sys.argv[2]
with tifffile.TiffFile(a_path) as ta, tifffile.TiffFile(b_path) as tb:
    a, b = ta.pages[0].asarray(), tb.pages[0].asarray()
    print('shape %s %s, dtype %s %s' % (a.shape, b.shape, a.dtype, b.dtype))
    if a.shape == b.shape and np.array_equal(a, b):
        print('pixels: identical (numpy.array_equal)')
    elif a.shape == b.shape:
        d = np.abs(a.astype(np.int64) - b.astype(np.int64))
        px = d.reshape(d.shape[0], d.shape[1], -1).max(axis=2) > 0
        print('pixels: differ at %.4f %% of pixels; largest difference %d of %d' % (
            100.0 * px.mean(), d.max(), np.iinfo(a.dtype).max if a.dtype.kind in 'ui' else 1))
    else:
        print('pixels: shapes differ')
    tags_a = {t.name: t.value for t in ta.pages[0].tags.values()}
    tags_b = {t.name: t.value for t in tb.pages[0].tags.values()}
    for name in sorted(set(tags_a) | set(tags_b)):
        va, vb = tags_a.get(name), tags_b.get(name)
        if name in ('StripOffsets', 'StripByteCounts', 'TileOffsets', 'TileByteCounts'):
            continue
        if isinstance(va, (bytes, str)) or isinstance(vb, (bytes, str)):
            if va != vb:
                sa, sb = str(va), str(vb)
                i = next((k for k in range(min(len(sa), len(sb))) if sa[k] != sb[k]), min(len(sa), len(sb)))
                print('tag %s differs at char %d: ...%r... vs ...%r...' % (name, i, sa[max(0, i - 60):i + 80], sb[max(0, i - 60):i + 80]))
        elif va != vb:
            print('tag %s differs' % name)
