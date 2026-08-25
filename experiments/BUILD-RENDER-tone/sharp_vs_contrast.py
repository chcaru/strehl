"""Did MY change soften the library, or did it lower contrast?

`trend.py`'s sharpness is the standard deviation of the first differences of the
mean channel. That statistic scales linearly with global contrast: multiply an
image by 0.95 and it reports 0.95, with no blur anywhere. So a tone change that
lowers contrast is indistinguishable from a blur under it, and a library-wide
"20 of 26 softer" is exactly what a small global contrast change looks like.

This separates them on the ONE comparison that isolates my change: the A/B pair
built from base a59ad57 differing only in image_out.rs. The full gallery run
spans two other lanes' commits as well and cannot answer this.

  raw    -- trend.py's metric, reproduced exactly, on the 8-bit view
  norm   -- the same metric after standardising each image to zero mean and
            unit variance, which removes any global gain and offset and leaves
            only genuine sharpness
  std    -- the global contrast itself, to show what moved

If raw falls and norm holds, the change is contrast, not blur.
"""

from pathlib import Path

import numpy as np
import tifffile

AB = Path(r"C:\dev\strehl-out\vtone-ab")


def read8(p: Path) -> np.ndarray:
    a = tifffile.imread(str(p))
    assert a.dtype == np.uint16, f"{p} is {a.dtype}, expected uint16"
    return (a >> 8).astype(np.float64)


def raw_sharp(y: np.ndarray) -> float:
    return float(np.sqrt(np.diff(y, axis=1).var() + np.diff(y, axis=0).var()))


def main() -> None:
    print(f'{"subject":<26}{"raw":>9}{"norm":>9}{"std":>9}   verdict')
    print("-" * 72)
    for b in sorted(AB.glob("*-before.tif")):
        s = b.name[: -len("-before.tif")]
        a = AB / f"{s}-after.tif"
        if not a.exists():
            continue
        yb, ya = read8(b).mean(2), read8(a).mean(2)
        rb, ra = raw_sharp(yb), raw_sharp(ya)
        sb, sa = float(yb.std()), float(ya.std())
        nb = raw_sharp((yb - yb.mean()) / sb)
        na = raw_sharp((ya - ya.mean()) / sa)
        raw_r, norm_r, std_r = ra / rb, na / nb, sa / sb
        verdict = "contrast, not blur" if norm_r > 0.995 else "REAL SOFTENING"
        print(f"{s:<26}{raw_r:9.4f}{norm_r:9.4f}{std_r:9.4f}   {verdict}")


if __name__ == "__main__":
    main()
