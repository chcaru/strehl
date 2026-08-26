"""What is actually in ORCH's `foam` master? Geometry, ceilings, and the shape
of the top of the histogram.

READ-ONLY on ORCH's files. This exists so that every later claim about "the
master's ceilings" is a number I read myself rather than one I quoted.

The point of interest is BUILD-CHROMA 25.2's `R 42213, G 38921, B 52239`: three
channels that terminate in three different places. If they were terminating at a
shared clamp they would be equal. This script reports the ceilings, the
population within 1% of each, and the per-channel value at a set of high
percentiles, so that "green runs out first" is visible as a shape and not only
as a maximum (a maximum is one pixel and could be a hot pixel).
"""

import sys

import numpy as np
import tifffile


def describe(path):
    a = tifffile.imread(path)
    print(f"  file      : {path}")
    print(f"  shape     : {a.shape}  dtype {a.dtype}")
    assert a.dtype == np.uint16, f"expected uint16, got {a.dtype}"
    f = a.astype(np.float32)
    names = "RGB"
    print(f"  {'chan':>4} {'max':>7} {'p99':>8} {'p99.9':>8} {'p99.99':>8} "
          f"{'>=0.99max':>10} {'>=0.999max':>11}")
    mx = []
    for c in range(3):
        v = f[..., c]
        m = float(v.max())
        mx.append(m)
        print(f"  {names[c]:>4} {m:7.0f} {np.percentile(v, 99):8.1f} "
              f"{np.percentile(v, 99.9):8.1f} {np.percentile(v, 99.99):8.1f} "
              f"{(v >= 0.99 * m).mean() * 100:9.4f}% {(v >= 0.999 * m).mean() * 100:10.4f}%")
    print(f"  ceilings  : R {mx[0]:.0f}  G {mx[1]:.0f}  B {mx[2]:.0f}")
    print(f"  B/G ceiling ratio : {mx[2] / mx[1]:.4f}   R/G : {mx[0] / mx[1]:.4f}")
    print(f"  full scale reached: {max(mx) / 65535.0 * 100:.2f}% of 65535")
    return mx


def main():
    for path in sys.argv[1:]:
        print("=" * 88)
        describe(path)
        print()


if __name__ == "__main__":
    main()
