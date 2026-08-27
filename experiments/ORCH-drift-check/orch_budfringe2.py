"""ORCH: local chroma extremes, not silhouette averages.

The first probe averaged (R-G, B-G) over the whole subject/background boundary and
returned a flat, slightly-negative profile -- no magenta. But the visual claim was
LOCAL: a rim on two pale bud tips. An average over a long boundary dilutes a defect
confined to a few edges, so a flat mean does not refute a local rim.

This probe reports EXTREMES over small windows on high-gradient pixels, and blows up
the suspect region so the claim can be checked by eye at the same time.

Controls, all on the same instrument:
  * a low-gradient interior region of the SAME image (a rim needs an edge)
  * the same statistic on subjects with no reported fringe
  * a shuffled-pixel version of the suspect region, which destroys spatial structure
    but preserves the colour histogram -- if the statistic survives the shuffle it is
    reading the palette, not a rim.
"""
import os
import numpy as np
from PIL import Image

ASSETS = r"C:\dev\strehl-out\VIEW-SHIP\assets"
OUT = r"C:\dev\strehl-out\VIEW-SHIP\assets"


def grad_mag(lum):
    gy = np.zeros_like(lum); gy[1:-1, :] = lum[2:, :] - lum[:-2, :]
    gx = np.zeros_like(lum); gx[:, 1:-1] = lum[:, 2:] - lum[:, :-2]
    return np.hypot(gx, gy)


def chroma_extremes(im, label, gthresh=60):
    R, G, B = im[:, :, 0], im[:, :, 1], im[:, :, 2]
    lum = im.mean(axis=2)
    g = grad_mag(lum)
    edge = g >= gthresh
    flat = g < 8
    n_e = int(edge.sum())
    if n_e < 200:
        print(f"    {label:38s} edge px={n_e:6d}  (too few, skipped)")
        return
    rg, bg = R - G, B - G
    # magenta score: both channels above green simultaneously
    mag = np.minimum(rg, bg)
    e_hi = np.percentile(mag[edge], 99.5)
    f_hi = np.percentile(mag[flat], 99.5) if flat.sum() > 200 else float("nan")
    frac = float((mag[edge] > 6).mean() * 100)
    print(f"    {label:38s} edge px={n_e:6d}  "
          f"magenta p99.5 edge={e_hi:7.2f}  flat={f_hi:7.2f}  "
          f"edge px>6DN={frac:5.2f}%")


def main():
    p = os.path.join(ASSETS, "flower-bud-alone-cpl--SHIP-V2--1to1.png")
    im = np.asarray(Image.open(p).convert("RGB")).astype(np.float64)
    print(f"flower-bud-alone 1:1 crop {im.shape}")

    print("\n  [A] suspect region (the pale bud tips I reacted to) vs rest")
    sus = im[20:220, 350:560]
    Image.fromarray(sus.astype(np.uint8)).resize(
        (sus.shape[1] * 3, sus.shape[0] * 3), Image.NEAREST
    ).save(os.path.join(OUT, "ORCH-budtip-3x.png"))
    print(f"    wrote ORCH-budtip-3x.png ({sus.shape[1]*3}x{sus.shape[0]*3}, 3x nearest)")
    chroma_extremes(sus, "suspect bud-tip region")
    chroma_extremes(im[430:700, 60:400], "interior control (same image)")

    print("\n  [B] shuffle control -- destroys structure, keeps histogram")
    rng = np.random.default_rng(7)
    sh = sus.reshape(-1, 3).copy()
    rng.shuffle(sh)
    chroma_extremes(sh.reshape(sus.shape), "suspect region, pixels shuffled")

    print("\n  [C] same statistic, subjects with no reported fringe")
    for fn, lab in [
        ("bee-3-cpl--SHIP-V2--1to1.png", "bee-3-cpl (showcase)"),
        ("wrapped-text-1--SHIP-V2--1to1.png", "wrapped-text-1 (showcase)"),
        ("coffee-bubbles--SHIP-V2--1to1.png", "coffee-bubbles (REPORTED fringe)"),
    ]:
        q = os.path.join(ASSETS, fn)
        if not os.path.exists(q):
            print(f"    {lab:38s} MISSING")
            continue
        chroma_extremes(np.asarray(Image.open(q).convert("RGB")).astype(np.float64), lab)


if __name__ == "__main__":
    main()
