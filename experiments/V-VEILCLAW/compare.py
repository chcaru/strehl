"""Side-by-side: what one raw frame saw vs what the master kept.

No demosaic library games. The raw green quincunx is filled to full resolution by
averaging the four orthogonal green neighbours at R/B sites, which keeps raw
coordinates exactly as raw_image_visible has them -- no crop margins, no flips.

The frame is then aligned to the master with an ECC similarity fit (the bracket
breathes, so a fixed offset will not do), and photometrically matched by a single
linear fit over the window. ONE display curve is derived from the pair and applied
to both, because deriving two curves is how you convince yourself of a difference
that is not there.

Usage:
  python compare.py --frame N --win y0 y1 x0 x1 --out DIR [--tag NAME]
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
    h, w = v.shape
    g = np.zeros_like(v)
    m = np.zeros((h, w), np.float32)
    g[0::2, 1::2] = v[0::2, 1::2]
    m[0::2, 1::2] = 1
    g[1::2, 0::2] = v[1::2, 0::2]
    m[1::2, 0::2] = 1
    k = np.array([[0, 1, 0], [1, 0, 1], [0, 1, 0]], np.float32)
    s = cv2.filter2D(g, -1, k, borderType=cv2.BORDER_REFLECT)
    c = cv2.filter2D(m, -1, k, borderType=cv2.BORDER_REFLECT)
    fill = s / np.maximum(c, 1e-6)
    return np.where(m > 0, g, fill)


def grade(a, lo, hi):
    x = np.clip((a - lo) / max(hi - lo, 1e-6), 0.0, 1.0)
    return (np.power(x, 1.0 / 2.2) * 255.0).astype(np.uint8)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frame", type=int, required=True)
    ap.add_argument("--win", nargs=4, type=int, required=True)
    ap.add_argument("--pad", type=int, default=400)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tag", default="cmp")
    a = ap.parse_args()
    y0, y1, x0, x1 = a.win
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    files = sorted(RAWDIR.glob("*.ARW"))
    f = files[a.frame]
    print(f"frame {a.frame} = {f.name}")

    M = tifffile.imread(str(MASTER))[:, :, 1].astype(np.float32)
    mst = M[y0:y1, x0:x1]

    G = green_full(f)
    p = a.pad
    sy0, sx0 = max(0, y0 - p), max(0, x0 - p)
    sy1, sx1 = min(G.shape[0], y1 + p), min(G.shape[1], x1 + p)
    src = G[sy0:sy1, sx0:sx1]

    # normalise both to 0..1 by their own white level for correlation only
    def n01(z):
        lo, hi = np.percentile(z, [0.5, 99.5])
        return np.clip((z - lo) / max(hi - lo, 1e-6), 0, 1).astype(np.float32)

    # coarse translation by NCC of the master window inside the padded source
    res = cv2.matchTemplate(cv2.GaussianBlur(n01(src), (0, 0), 6),
                            cv2.GaussianBlur(n01(mst), (0, 0), 6), cv2.TM_CCOEFF_NORMED)
    _, mx, _, loc = cv2.minMaxLoc(res)
    dx, dy = loc[0] - (x0 - sx0), loc[1] - (y0 - sy0)
    print(f"coarse NCC {mx:.3f} at shift dy={dy} dx={dx}")

    # refine to an affine transform mapping master coords -> frame coords
    # (the bracket breathes: translation alone will not register it)
    warp = np.array([[1, 0, dx], [0, 1, dy]], np.float32)
    ph, pw = src.shape
    ref_pad = np.zeros((ph, pw), np.float32)
    ref_pad[y0 - sy0:y0 - sy0 + (y1 - y0), x0 - sx0:x0 - sx0 + (x1 - x0)] = \
        cv2.GaussianBlur(n01(mst), (0, 0), 3)
    mask = np.zeros((ph, pw), np.uint8)
    mask[y0 - sy0:y0 - sy0 + (y1 - y0), x0 - sx0:x0 - sx0 + (x1 - x0)] = 1
    mov = cv2.GaussianBlur(n01(src), (0, 0), 3)
    crit = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 300, 1e-7)
    for mode in (cv2.MOTION_AFFINE, cv2.MOTION_EUCLIDEAN):
        try:
            w0 = warp.copy()
            cc, w0 = cv2.findTransformECC(ref_pad, mov, w0, mode, crit, mask, 5)
            warp = w0
            print(f"ECC mode={mode} cc={cc:.4f}\n{warp}")
            break
        except cv2.error as e:
            print(f"ECC mode={mode} failed: {e}")

    aligned = cv2.warpAffine(src, warp, (pw, ph),
                             flags=cv2.INTER_LANCZOS4 | cv2.WARP_INVERSE_MAP,
                             borderMode=cv2.BORDER_REPLICATE)
    frm = aligned[y0 - sy0:y0 - sy0 + (y1 - y0), x0 - sx0:x0 - sx0 + (x1 - x0)]

    # single photometric anchor: the paper background, which is physically the
    # same white in both images. Both are linear with true black at 0, so a
    # gain is the whole transform. Percentile MATCHING is wrong here -- the
    # master contains dark foreground the frame does not, which drags the fit.
    fw = float(np.percentile(frm, 99.5))
    mw = float(np.percentile(mst, 99.5))
    gain, off = mw / max(fw, 1e-6), 0.0
    frm_m = frm * gain + off
    print(f"paper-white anchor: frame p99.5={fw:.0f} master p99.5={mw:.0f} gain={gain:.4f}")

    lo, hi = 0.0, float(np.percentile(np.concatenate([frm_m.ravel(), mst.ravel()]), 99.7))
    print(f"shared display curve lo={lo:.0f} hi={hi:.0f}")
    a8, b8 = grade(frm_m, lo, hi), grade(mst, lo, hi)

    h, w = a8.shape
    canvas = Image.new("RGB", (w * 2 + 24, h + 34), (24, 24, 24))
    canvas.paste(Image.fromarray(a8).convert("RGB"), (0, 30))
    canvas.paste(Image.fromarray(b8).convert("RGB"), (w + 24, 30))
    d = ImageDraw.Draw(canvas)
    d.text((6, 8), f"FRAME {a.frame} ({f.stem}) aligned+photometrically matched",
           fill=(255, 220, 120))
    d.text((w + 30, 8), "MASTER bee-3-cpl.tiff", fill=(255, 220, 120))
    canvas.save(out / f"{a.tag}--sidebyside-f{a.frame:03d}.png")

    Image.fromarray(a8).save(out / f"{a.tag}--frame{a.frame:03d}.png")
    Image.fromarray(b8).save(out / f"{a.tag}--master.png")

    # numbers: local contrast + detail
    def lap(z):
        z = z.astype(np.float32)
        return float(np.abs(4 * z[1:-1, 1:-1] - z[:-2, 1:-1] - z[2:, 1:-1]
                            - z[1:-1, :-2] - z[1:-1, 2:]).mean())

    wl = np.percentile(mst, 99.0)
    print(f"\n{'':<10}{'p2':>12}{'p50':>12}{'white p99':>12}{'|lap|':>12}{'p2/white':>12}")
    for nm, z in (("frame", frm_m), ("master", mst)):
        p2, p50, p99 = np.percentile(z, [2, 50, 99])
        print(f"{nm:<10}{p2:12.0f}{p50:12.0f}{p99:12.0f}{lap(z):12.2f}{p2 / max(wl, 1):12.3f}")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
