"""Responsiveness control for the P3 black/NaN sweep.

At 8 bits the JITTER6 arm read 0.00068% black and I took that as proof the
sweep could see a rim. It could not: at true 16 bits that arm reads 0.00000%
like every other, because the 8-bit reader truncates 1..255 to 0. So the sweep's
null had no plant behind it, which is exactly the failure discipline 598 names --
a reading of 0.000 is as likely to be a disconnected probe as a correct null.

This plants known black into a real render, on the same reader and the same
code path, and asserts the sweep finds exactly what was planted.
"""

import sys

import numpy as np
import tifffile

from blacksweep import sweep


def main(argv: list[str]) -> int:
    src, dst = argv[1], argv[2]
    a = tifffile.imread(src)
    assert a.dtype == np.uint16, a.dtype
    h, w = a.shape[:2]

    before = sweep(src)
    assert before["black_count"] == 0, f"{src} already has black; pick another arm"

    # 9 interior pixels, and 9 in the outer annulus where a gather rim lives.
    a[h // 2 : h // 2 + 3, w // 2 : w // 2 + 3, :] = 0
    a[1:4, 1:4, :] = 0
    tifffile.imwrite(dst, a)

    after = sweep(dst)
    expect_total, expect_ann = 18, 9
    ok = (
        after["black_count"] == expect_total
        and after["annulus_black_count"] == expect_ann
    )
    print(f"planted   : {expect_total} black px ({expect_ann} of them in the annulus)")
    print(
        f"recovered : {after['black_count']} black px "
        f"({after['annulus_black_count']} in the annulus)"
    )
    print(
        f"fractions : whole {after['black_frac_pct']:.7f}%  "
        f"outer {after['annulus_black_frac_pct']:.7f}%"
    )
    print("PLANT RECOVERED -- the sweep is live" if ok else "PLANT LOST -- sweep is dead")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
