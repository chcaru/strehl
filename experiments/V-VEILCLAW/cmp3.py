"""Three-way: the foreground-layer frame, the background-layer frame, and the master.

One alignment method, one paper-white anchor per image, ONE display curve derived
from all three and applied to all three. Anything less and a tonal difference you
see is a difference you made.
"""
import argparse
import pathlib

import cv2
import numpy as np
import rawpy
import tifffile
from PIL import Image, ImageDraw

RAWDIR = pathlib.Path(r"D:\personal\macro\bee-3-cpl")
MASTER = pathlib.Path(r"C:\dev\strehl-out\SHIP-V1\bee-3-cpl.tiff")


def green_full(path):
    with rawpy.imread(str(path)) as r:
        v = r.raw_image_visible.astype(np.float32)
        black = float(np.mean(r.black_level_per_channel))
    v = v - black
    g = np.zeros_like(v)
    m = np.zeros(v.shape, np.float32)
    g[0::2, 1::2] = v[0::2, 1::2]
    m[0::2, 1::2] = 1
    g[1::2, 0::2] = v[1::2, 0::2]
    m[1::2, 0::2] = 1
    k = np.array([[0, 1, 0], [1, 0, 1], [0, 1, 0]], np.float32)
    s = cv2.filter2D(g, -1, k, borderType=cv2.BORDER_REFLECT)
    c = cv2.filter2D(m, -1, k, borderType=cv2.BORDER_REFLECT)
    return np.where(m > 0, g, s / np.maximum(c, 1e-6))


def n01(z):
    lo, hi = np.percentile(z, [0.5, 99.5])
    return np.clip((z - lo) / max(hi - lo, 1e-6), 0, 1).astype(np.float32)


def lap(z):
    z = z.astype(np.float32)
    return float(np.abs(4 * z[1:-1, 1:-1] - z[:-2, 1:-1] - z[2:, 1:-1]
                        - z[1:-1, :-2] - z[1:-1, 2:]).mean())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", required=True)
    ap.add_argument("--win", nargs=4, type=int, required=True)
    ap.add_argument("--claw", nargs=4, type=int, required=True,
                    help="tight box on the claw body, master coords, for the numbers")
    ap.add_argument("--pad", type=int, default=420)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tag", default="tri")
    a = ap.parse_args()
    y0, y1, x0, x1 = a.win
    ky0, ky1, kx0, kx1 = a.claw
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    files = sorted(RAWDIR.glob("*.ARW"))
    M = tifffile.imread(str(MASTER))[:, :, 1].astype(np.float32)
    mst = M[y0:y1, x0:x1]

    panels = []
    for spec in a.frames.split(","):
        parts = spec.split(":")
        k = int(parts[0])
        G = green_full(files[k])
        p = a.pad
        sy0, sx0 = max(0, y0 - p), max(0, x0 - p)
        sy1, sx1 = min(G.shape[0], y1 + p), min(G.shape[1], x1 + p)
        src = G[sy0:sy1, sx0:sx1]
        if len(parts) == 3:
            dy, dx, note = int(parts[1]), int(parts[2]), "forced"
        else:
            r = cv2.matchTemplate(cv2.GaussianBlur(n01(src), (0, 0), 4),
                                  cv2.GaussianBlur(n01(mst), (0, 0), 4), cv2.TM_CCOEFF_NORMED)
            _, mx, _, loc = cv2.minMaxLoc(r)
            dy, dx, note = loc[1] - (y0 - sy0), loc[0] - (x0 - sx0), f"ncc={mx:.3f}"
        oy, ox = dy + (y0 - sy0), dx + (x0 - sx0)
        crop = src[oy:oy + (y1 - y0), ox:ox + (x1 - x0)]
        print(f"frame {k}: {note} dy={dy} dx={dx}")
        panels.append((f"FRAME {k} ({files[k].stem})", crop, (dy, dx)))
    panels.append(("MASTER bee-3-cpl.tiff", mst, (0, 0)))

    # paper-white anchor per image, then one shared curve
    norm = []
    for lab, z, _ in panels:
        w = float(np.percentile(z, 99.5))
        norm.append((lab, z / max(w, 1e-6)))
    hi = float(max(np.percentile(z, 99.9) for _, z in norm))

    def grade(z):
        return (np.power(np.clip(z / hi, 0, 1), 1 / 2.2) * 255).astype(np.uint8)

    h, w = norm[0][1].shape
    n = len(norm)
    canvas = Image.new("RGB", (w * n + 12 * (n - 1), h + 34), (22, 22, 22))
    d = ImageDraw.Draw(canvas)
    for i, (lab, z) in enumerate(norm):
        canvas.paste(Image.fromarray(grade(z)).convert("RGB"), (i * (w + 12), 30))
        d.text((i * (w + 12) + 6, 8), lab, fill=(255, 210, 110))
    canvas.save(out / f"{a.tag}--triptych.png")

    print(f"\nclaw box master y[{ky0}:{ky1}] x[{kx0}:{kx1}] "
          f"(local y[{ky0 - y0}:{ky1 - y0}] x[{kx0 - x0}:{kx1 - x0}])")
    print(f"{'':<28}{'claw p5/paper':>16}{'claw mean/paper':>18}{'claw |lap|':>13}")
    for (lab, z), (_, raw, _) in zip(norm, panels):
        c = z[ky0 - y0:ky1 - y0, kx0 - x0:kx1 - x0]
        print(f"{lab:<28}{np.percentile(c, 5):16.3f}{c.mean():18.3f}{lap(c) * 1000:13.1f}")
    print(f"\nwrote {out / (a.tag + '--triptych.png')}")


if __name__ == "__main__":
    main()
