"""Where in the frequency stack did the claw lose its contrast?

If the master's fine detail matches the frame that resolved the claw but its
low-frequency base matches the frame that was focused on the foreground hairs,
the merge did not lose the detail -- it sat that detail on top of the wrong
pedestal. That is a veiling failure with a specific, addressable location in the
pipeline, and it is different from "the detail is gone".

All planes are normalised by their own paper white before comparison, so a
number here is a fraction of paper luminance and is directly comparable.
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--win", nargs=4, type=int, required=True)
    ap.add_argument("--spec", required=True,
                    help="frame[:dy:dx],... ; give dy/dx to override NCC alignment")
    ap.add_argument("--pad", type=int, default=420)
    ap.add_argument("--sigma", type=float, default=32.0)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tag", default="unmix")
    a = ap.parse_args()
    y0, y1, x0, x1 = a.win
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    files = sorted(RAWDIR.glob("*.ARW"))
    M = tifffile.imread(str(MASTER))[:, :, 1].astype(np.float32)
    mst = M[y0:y1, x0:x1]

    planes = []
    for spec in a.spec.split(","):
        parts = spec.split(":")
        k = int(parts[0])
        G = green_full(files[k])
        p = a.pad
        sy0, sx0 = max(0, y0 - p), max(0, x0 - p)
        sy1, sx1 = min(G.shape[0], y1 + p), min(G.shape[1], x1 + p)
        src = G[sy0:sy1, sx0:sx1]
        if len(parts) == 3:
            dy, dx = int(parts[1]), int(parts[2])
            note = "forced"
        else:
            r = cv2.matchTemplate(cv2.GaussianBlur(n01(src), (0, 0), 4),
                                  cv2.GaussianBlur(n01(mst), (0, 0), 4), cv2.TM_CCOEFF_NORMED)
            _, mx, _, loc = cv2.minMaxLoc(r)
            dy, dx = loc[1] - (y0 - sy0), loc[0] - (x0 - sx0)
            note = f"ncc={mx:.3f}"
        oy, ox = dy + (y0 - sy0), dx + (x0 - sx0)
        crop = src[oy:oy + (y1 - y0), ox:ox + (x1 - x0)]
        print(f"frame {k}: {note} dy={dy} dx={dx}")
        planes.append((f"f{k:03d}", crop))
    planes.append(("master", mst))

    norm = [(n, z / max(float(np.percentile(z, 99.5)), 1e-6)) for n, z in planes]

    print(f"\nlow/high split at sigma={a.sigma} px, values as a fraction of paper white")
    print(f"{'plane':<10}{'base mean':>12}{'base p5':>10}{'detail rms':>12}{'detail p1':>11}")
    rows = {}
    for n, z in norm:
        base = cv2.GaussianBlur(z, (0, 0), a.sigma)
        det = z - base
        rows[n] = (base, det)
        print(f"{n:<10}{base.mean():12.3f}{np.percentile(base, 5):10.3f}"
              f"{det.std():12.4f}{np.percentile(det, 1):11.4f}")

    names = [n for n, _ in norm]
    # cross-correlate detail layers against the master's detail layer
    dm = rows["master"][1]
    print()
    for n in names[:-1]:
        d = rows[n][1]
        c = float(np.corrcoef(d.ravel(), dm.ravel())[0, 1])
        s = float((d * dm).sum() / max((d * d).sum(), 1e-9))
        print(f"detail corr(master, {n}) = {c:+.3f}   "
              f"master_detail ~= {s:.2f} x {n}_detail   "
              f"(rms ratio {rows[n][1].std() and dm.std() / rows[n][1].std():.2f})")

    # visual: base and detail panels, one curve each row
    h, w = norm[0][1].shape
    cols = len(norm)
    canvas = Image.new("RGB", (cols * (w + 10), 2 * (h + 30)), (20, 20, 20))
    d = ImageDraw.Draw(canvas)
    bhi = max(rows[n][0].max() for n in names)
    for i, n in enumerate(names):
        b = (np.clip(rows[n][0] / bhi, 0, 1) ** (1 / 2.2) * 255).astype(np.uint8)
        det = np.clip(rows[n][1] * 4 + 0.5, 0, 1)
        e = (det * 255).astype(np.uint8)
        canvas.paste(Image.fromarray(b).convert("RGB"), (i * (w + 10), 26))
        canvas.paste(Image.fromarray(e).convert("RGB"), (i * (w + 10), h + 56))
        d.text((i * (w + 10) + 6, 6), f"{n} BASE (sigma {a.sigma:.0f})", fill=(255, 210, 110))
        d.text((i * (w + 10) + 6, h + 36), f"{n} DETAIL x4", fill=(120, 220, 255))
    canvas.save(out / f"{a.tag}--basedetail.png")
    print(f"\nwrote {out / (a.tag + '--basedetail.png')}")


if __name__ == "__main__":
    main()
