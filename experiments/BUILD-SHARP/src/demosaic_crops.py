"""Visual crops for the malvar-vs-directional demosaic A/B.

The numeric verdict in demosaic_noise_or_detail.py is that the directional
green amplifies out-of-focus noise and buys nothing where detail lives.  That
claim was numeric only, and this project's standing rule is to look at the
picture.  This writes the two crops that decide it:

  * the flattest tile the MALVAR arm can find (out of focus -- there is no
    detail there to recover, so any visible rise is noise), and
  * the sharpest tile the MALVAR arm can find (a detail site -- if the
    directional green is a sharpness win, it is visible here or nowhere).

Tiles are ranked on the malvar arm alone so the selection cannot be biased by
the arm under test, exactly as in demosaic_noise_or_detail.py.

Crops are written as 16-bit PNG at 4x nearest-neighbour so that the comparison
is between pixels and not between a viewer's resampling kernels.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import tifffile

OUT = Path(r"C:\dev\strehl-out\BUILD-SHARP\demo-ab")
TILE = 128
ZOOM = 4


def green(path: Path) -> np.ndarray:
    """Green plane as float32.  Green only: it is the plane the directional
    estimator actually changes, and the plane that survives cross-build
    comparison (the chromatic-aberration correction moves red and blue)."""
    a = tifffile.imread(str(path))
    if a.ndim != 3 or a.shape[2] < 3:
        raise SystemExit(f"{path}: expected an RGB image, got {a.shape}")
    return a[:, :, 1].astype(np.float32)


def tile_scores(g: np.ndarray) -> tuple[np.ndarray, list[tuple[int, int]]]:
    """Mean gradient magnitude per non-overlapping TILE x TILE tile."""
    h, w = g.shape
    coords: list[tuple[int, int]] = []
    scores: list[float] = []
    for y in range(0, h - TILE + 1, TILE):
        for x in range(0, w - TILE + 1, TILE):
            t = g[y : y + TILE, x : x + TILE]
            dy = np.diff(t, axis=0)
            dx = np.diff(t, axis=1)
            scores.append(float(np.abs(dy).mean() + np.abs(dx).mean()))
            coords.append((y, x))
    return np.asarray(scores), coords


def stretch(t: np.ndarray, lo: float, hi: float) -> np.ndarray:
    """Map [lo, hi] to full 16-bit range.  Both arms of a pair are stretched
    with the SAME lo/hi, taken from the malvar arm, so that a difference on
    screen is a difference in the data and not in the normalisation."""
    if hi <= lo:
        hi = lo + 1.0
    v = (t - lo) / (hi - lo)
    return np.clip(v, 0.0, 1.0)


def write_pair(name: str, a: np.ndarray, b: np.ndarray, y: int, x: int) -> None:
    ta = a[y : y + TILE, x : x + TILE]
    tb = b[y : y + TILE, x : x + TILE]
    lo, hi = float(ta.min()), float(ta.max())
    sa = stretch(ta, lo, hi)
    sb = stretch(tb, lo, hi)
    # side by side: malvar | 8px white rule | directional
    rule = np.ones((TILE, 8), dtype=np.float32)
    joined = np.concatenate([sa, rule, sb], axis=1)
    big = np.repeat(np.repeat(joined, ZOOM, axis=0), ZOOM, axis=1)
    u16 = (big * 65535.0 + 0.5).astype(np.uint16)
    dst = OUT / f"crop-{name}.png"
    tifffile.imwrite(str(dst.with_suffix(".tif")), u16)
    print(f"  wrote {dst.with_suffix('.tif').name}  tile=({y},{x})  "
          f"stretch=[{lo:.0f},{hi:.0f}]  left=malvar right=directional")


def main() -> int:
    subjects = [
        ("bee-3-cpl", OUT / "bee-3-cpl--malvar.tif", OUT / "bee-3-cpl--directional.tif"),
        ("tweezers-cpl", OUT / "tweezers-cpl--malvar.tif", OUT / "tweezers-cpl--directional.tif"),
    ]
    for name, pm, pd in subjects:
        if not pm.exists() or not pd.exists():
            raise SystemExit(f"missing render arm for {name}")
        print(f"{name}:")
        m = green(pm)
        d = green(pd)
        if m.shape != d.shape:
            raise SystemExit(f"{name}: arms differ in shape {m.shape} vs {d.shape}")
        # Non-vacuity: the two arms must actually differ, or a "no visible
        # difference" reading below would be trivially true.
        md = float(np.abs(m - d).max())
        print(f"  max|malvar - directional| on green = {md:.1f} DN")
        if md == 0.0:
            raise SystemExit(f"{name}: arms are identical -- the A/B is vacuous")
        s, coords = tile_scores(m)
        order = np.argsort(s)
        flat_y, flat_x = coords[int(order[len(order) // 40])]  # ~2.5th pct, avoids pure black
        sharp_y, sharp_x = coords[int(order[-1])]
        write_pair(f"{name}-flat", m, d, flat_y, flat_x)
        write_pair(f"{name}-sharp", m, d, sharp_y, sharp_x)
    return 0


if __name__ == "__main__":
    sys.exit(main())
