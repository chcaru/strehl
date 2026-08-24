"""Contact sheet of the arms, so an artefact cannot hide behind a ratio.

radial4.py reported GAINED at 24.5x ZOOMNULL in the outermost radius band.
A 24x sharpness gain is not physically plausible, and a boundary artefact
reading as a sharpness win is precisely how M86's first render produced a fake
1.4565x. So: look before claiming.
"""

import sys

import numpy as np
import tifffile
from PIL import Image, ImageDraw


def prep(path: str, w: int) -> np.ndarray:
    a = tifffile.imread(path)
    g = a[:, :, 1] if a.ndim == 3 else a
    h0, w0 = g.shape
    f = max(1, w0 // w)
    h1, w1 = (h0 // f) * f, (w0 // f) * f
    d = g[:h1, :w1].reshape(h1 // f, f, w1 // f, f).mean(axis=(1, 3))
    lo, hi = np.percentile(d, 0.5), np.percentile(d, 99.5)
    return np.clip((d - lo) / max(hi - lo, 1e-9), 0, 1)


def main(argv: list[str]) -> int:
    out, base = argv[1], argv[2]
    names = argv[3:]
    tiles = []
    for n in names:
        d = prep(rf"{base}\marker-{n}.tif", 640)
        im = Image.fromarray((d * 255).astype(np.uint8)).convert("RGB")
        ImageDraw.Draw(im).text((6, 4), n, fill=(255, 255, 0))
        tiles.append(np.asarray(im))
        print(f"{n:<10} {d.shape}  mean {d.mean():.4f}  "
              f"frac<0.02 {float((d < 0.02).mean()):.5f}  "
              f"frac>0.98 {float((d > 0.98).mean()):.5f}")
    n2 = (len(tiles) + 1) // 2
    rows = [np.concatenate(tiles[i * 2:i * 2 + 2], axis=1) for i in range(n2)
            if len(tiles[i * 2:i * 2 + 2]) == 2]
    Image.fromarray(np.concatenate(rows, axis=0)).save(out)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
