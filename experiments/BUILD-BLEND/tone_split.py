"""How do the two arms differ in TONE, and is that difference global or local?

A large mean difference between the arms has two very different explanations
and they need separating before anything is claimed:

* **Global.** This renderer skips the shipped path's per-frame photometric gain
  fit. A merge whose base band is close to a mean across frames turns
  un-normalised gain drift into an overall exposure shift -- benign, uniform,
  and correctable with one number.
* **Local.** A difference that varies across the frame is the interesting kind:
  it is where the merges actually disagree about the scene.

So this fits ONE global affine transform (gain and offset) by least squares,
reports how much of the difference that explains, and reports what is left.
The residual is the honest measure of how much the two arms genuinely disagree.

Deliberately NOT a quality score. Gradient energy and high-pass energy have both
lied on this project by being satisfied by injected structure, and nothing here
is used to decide which arm is better -- the pictures decide that. This only
separates "different exposure" from "different picture".
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import tifffile


def read(path: Path, step: int = 4) -> np.ndarray:
    a = tifffile.imread(path)
    assert a.dtype == np.uint16, f"{path} is {a.dtype}, expected uint16"
    return a[::step, ::step, :].astype(np.float64)


def main() -> int:
    ctrl, blend = Path(sys.argv[1]), Path(sys.argv[2])
    a, b = read(ctrl), read(blend)
    assert a.shape == b.shape

    raw = float(np.abs(a - b).mean())
    # Least squares b ~ g*a + o, over all three channels jointly.
    x, y = a.ravel(), b.ravel()
    g, o = np.polyfit(x, y, 1)
    resid = float(np.abs(y - (g * x + o)).mean())

    print(f"control            : {ctrl.name}")
    print(f"blend              : {blend.name}")
    print(f"mean|blend-control|: {raw:8.1f} DN  ({100 * raw / 65535:.2f}% of full scale)")
    print(f"best global fit    : blend ~ {g:.4f} x control {o:+.1f} DN")
    print(f"residual after it  : {resid:8.1f} DN  ({100 * resid / 65535:.2f}% of full scale)")
    print(f"explained by tone  : {100 * (1 - resid / raw):5.1f}%")
    for i, ch in enumerate("RGB"):
        ca, cb = a[:, :, i].mean(), b[:, :, i].mean()
        print(f"  mean {ch}           : control {ca:8.1f}   blend {cb:8.1f}   ({cb - ca:+.1f} DN)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
