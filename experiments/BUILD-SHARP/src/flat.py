"""Find the flattest large background region and crop every arm there.

The patchwork/brightness-step defect is a claim about FLAT regions: neighbouring
areas that should hold a smooth gradient instead land on different mean levels.
Cropping by hand risks aiming at texture, where the defect cannot be seen, or
worse, aiming at a place chosen because it looked bad in one arm -- which biases
the comparison toward that arm.

So the location is chosen by a rule that consults only the REFERENCE arm and
only asks "is this flat", never "is this different between arms". The statistic
picks WHERE to look; it does not deliver the verdict. Judgement stays on the
picture, per the standing rule and corpus fact 1359, where a Laplacian metric
scored a visible selection artefact 2.73x above the correct render.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image


def read16(path: Path) -> np.ndarray:
    a = tifffile.imread(str(path))
    if a.dtype != np.uint16:
        raise SystemExit(f"{path}: expected uint16, got {a.dtype}")
    return a


def srgb(lin: np.ndarray) -> np.ndarray:
    a = 0.055
    return np.where(lin <= 0.0031308, 12.92 * lin,
                    (1 + a) * np.power(np.maximum(lin, 0.0), 1 / 2.4) - a)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--ref", required=True)
    p.add_argument("--arms", nargs="+", required=True)
    p.add_argument("--outdir", required=True)
    p.add_argument("--size", type=int, default=1100)
    p.add_argument("--gain", type=float, required=True)
    p.add_argument("--top", type=int, default=2)
    a = p.parse_args()

    ref = read16(Path(a.ref))
    f = ref.astype(np.float64) / 65535.0
    y = 0.2126 * f[..., 0] + 0.7152 * f[..., 1] + 0.0722 * f[..., 2]
    h, w = y.shape
    s, step = a.size, a.size // 2

    # Flatness = low local gradient energy. Require the window to be bright, so
    # we land on the defocused background rather than on a dark in-focus mass
    # that is also gradient-free.
    cands = []
    for yy in range(0, h - s, step):
        for xx in range(0, w - s, step):
            t = y[yy:yy + s, xx:xx + s]
            g = np.mean(np.abs(np.diff(t[::4, ::4], axis=0))) + \
                np.mean(np.abs(np.diff(t[::4, ::4], axis=1)))
            if t.mean() > np.percentile(y, 60):
                cands.append((g, xx, yy, float(t.mean())))
    cands.sort()
    out = Path(a.outdir)
    out.mkdir(parents=True, exist_ok=True)

    for rank, (g, xx, yy, mu) in enumerate(cands[: a.top]):
        print(f"flat{rank}: x={xx} y={yy} grad={g:.6f} mean={mu:.4f}")
        for spec in a.arms:
            name, path = spec.split("=", 1)
            rgb = read16(Path(path))[yy:yy + s, xx:xx + s]
            v = rgb.astype(np.float64) / 65535.0 * a.gain
            img = Image.fromarray((np.clip(srgb(v), 0, 1) * 255 + 0.5).astype(np.uint8))
            img.save(out / f"flat{rank}-{name}.png")


if __name__ == "__main__":
    main()
