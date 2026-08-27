"""ORCH: the fringe is real; both my probes missed it. Gate on CHROMA, not luma.

Probe 1 averaged (R-G,B-G) over the whole silhouette -> diluted a rim confined to a
few edges. Probe 2 gated on |grad luma| >= 60 -> returned edge px = 0 on this subject,
because the rim lives on a PALE BUD against a WHITE background, which is a
low-luma-contrast, HIGH-chroma-contrast boundary. A luma-gradient gate is structurally
blind to exactly the defect class being hunted.

Visual ground truth: ORCH-budtip-3x.png shows an unmistakable pink line hugging the
bud silhouette. Any probe that reports "no fringe" here is refuted by that image.

This probe gates on the gradient of the chroma channels themselves.

Controls (all must be reported, pass or fail):
  * shuffle      - destroys structure, keeps histogram; must kill the signal
  * interior     - low-gradient region of the same image; must be quiet
  * showcase     - bee-3-cpl / wrapped-text-1, no reported fringe
  * reported     - coffee-bubbles, dry-erase, foam: fringe reported
A statistic that does not separate 'reported' from 'showcase' is NOT commissioned and
its verdicts must not be quoted.
"""
import os
import numpy as np
from PIL import Image

ASSETS = r"C:\dev\strehl-out\VIEW-SHIP\assets"


def gmag(a):
    gy = np.zeros_like(a); gy[1:-1, :] = a[2:, :] - a[:-2, :]
    gx = np.zeros_like(a); gx[:, 1:-1] = a[:, 2:] - a[:, :-2]
    return np.hypot(gx, gy)


def score(im, label, cthresh=8.0):
    R, G, B = im[:, :, 0], im[:, :, 1], im[:, :, 2]
    rg, bg = R - G, B - G
    cg = np.maximum(gmag(rg), gmag(bg))       # chroma-gradient gate
    lg = gmag(im.mean(axis=2))                # luma gradient, for comparison only
    edge = cg >= cthresh
    n = int(edge.sum())
    if n < 100:
        print(f"  {label:40s} chroma-edge px={n:6d}  (too few)")
        return None
    mag = np.minimum(rg, bg)                  # magenta = both above green
    p = float(np.percentile(mag[edge], 99.5))
    frac = float((mag[edge] > 6).mean() * 100)
    # how many of these chroma edges would a LUMA gate have seen?
    seen_by_luma = float((lg[edge] >= 60).mean() * 100)
    print(f"  {label:40s} chroma-edge px={n:6d}  magenta p99.5={p:7.2f}  "
          f">6DN={frac:5.2f}%   luma-gate would see {seen_by_luma:5.1f}%")
    return p, frac


def main():
    bud = np.asarray(Image.open(
        os.path.join(ASSETS, "flower-bud-alone-cpl--SHIP-V2--1to1.png")
    ).convert("RGB")).astype(np.float64)

    print("SUSPECT + within-image controls")
    sus = bud[20:220, 350:560]
    score(sus, "bud-tip region (rim visible at 3x)")
    score(bud[430:700, 60:400], "interior control, same image")
    rng = np.random.default_rng(7)
    sh = sus.reshape(-1, 3).copy(); rng.shuffle(sh)
    score(sh.reshape(sus.shape), "bud-tip region, pixels SHUFFLED")

    print("\nCROSS-SUBJECT: does the statistic separate reported from showcase?")
    for fn, lab in [
        ("flower-bud-alone-cpl--SHIP-V2--1to1.png", "flower-bud-alone  [reported fringe]"),
        ("coffee-bubbles--SHIP-V2--1to1.png",       "coffee-bubbles    [reported fringe]"),
        ("foam--SHIP-V2--1to1.png",                 "foam              [reported fringe]"),
        ("dry-erase-marker-head-cpl--SHIP-V2--1to1.png", "dry-erase-marker  [reported fringe]"),
        ("bee-3-cpl--SHIP-V2--1to1.png",            "bee-3-cpl         [showcase]"),
        ("bee-2-cpl--SHIP-V2--1to1.png",            "bee-2-cpl         [showcase]"),
        ("wrapped-text-1--SHIP-V2--1to1.png",       "wrapped-text-1    [showcase]"),
        ("leaf-2-cpl--SHIP-V2--1to1.png",           "leaf-2-cpl        [showcase]"),
    ]:
        p = os.path.join(ASSETS, fn)
        if not os.path.exists(p):
            print(f"  {lab:40s} MISSING")
            continue
        score(np.asarray(Image.open(p).convert("RGB")).astype(np.float64), lab)


if __name__ == "__main__":
    main()
