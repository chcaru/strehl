"""Report the value distribution and header of a linear-sRGB u16 TIFF.

Used to check that the per-frame develop that feeds Zerene (a) actually fills a
useful part of the u16 range, so that quantisation is not the confound, and
(b) is not clipping at either end, since a clipped sample is a nonlinearity and
this whole lane exists to remove nonlinearities.
"""
import sys

import numpy as np
import tifffile


def main():
    for path in sys.argv[1:]:
        with tifffile.TiffFile(path) as tf:
            p = tf.pages[0]
            desc = {t.name: t.value for t in p.tags
                    if t.name in ("ImageWidth", "ImageLength", "BitsPerSample",
                                  "SampleFormat", "PhotometricInterpretation",
                                  "Compression", "SamplesPerPixel",
                                  "InterColorProfile", "Software",
                                  "ImageDescription")}
            for k in ("InterColorProfile",):
                if k in desc:
                    desc[k] = f"<{len(desc[k])} bytes>"
        a = tifffile.imread(path)
        print("=" * 90)
        print(path)
        print(f"  shape {a.shape} dtype {a.dtype}")
        for k, v in desc.items():
            print(f"  {k:26s} {v}")
        for c, nm in enumerate("RGB"):
            v = a[:, :, c].ravel()
            q = np.percentile(v, [0, 0.1, 50, 99, 99.9, 100])
            print(f"  {nm}: min {q[0]:7.0f} p0.1 {q[1]:7.0f} med {q[2]:7.0f} "
                  f"p99 {q[3]:7.0f} p99.9 {q[4]:7.0f} max {q[5]:7.0f}  "
                  f"n==0 {int((v == 0).sum())}  n==65535 {int((v == 65535).sum())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
