"""ORCH: is the magenta rim on flower-bud-alone real, and is it specular-only?

Presence test only. The input is an sRGB, tone-mapped 1:1 crop, so magnitudes here
are NOT physical -- per the standing rule, never quote amplitudes off an --srgb
render. The question is strictly: does a narrow band at the subject/white boundary
carry a chroma signature that the interior does not?

Method: find the silhouette against the blown background, walk inward, and report
mean (R-G) and (B-G) as a function of distance from the boundary. A magenta rim is
R-G > 0 AND B-G > 0 in a narrow band that decays inward.

Controls:
  * interior band far from any boundary (should be ~flat, green-dominant)
  * the SAME profile computed on a subject with no reported fringe (bee-3-cpl),
    which must NOT show the narrow positive band, or the profile is measuring the
    demosaic/tone pipeline rather than this subject's defect.
"""
import sys
import numpy as np
from PIL import Image

ASSETS = r"C:\dev\strehl-out\VIEW-SHIP\assets"


def profile(path, label, white_thresh=245, maxdist=14):
    im = np.asarray(Image.open(path).convert("RGB")).astype(np.float64)
    R, G, B = im[:, :, 0], im[:, :, 1], im[:, :, 2]
    lum = im.mean(axis=2)

    bg = lum >= white_thresh          # blown background
    fg = ~bg
    if bg.sum() < 500 or fg.sum() < 500:
        print(f"  {label}: SKIP - bg={bg.sum()} fg={fg.sum()} px, no usable silhouette")
        return None

    # distance from every foreground pixel to the nearest background pixel,
    # computed by iterative dilation of the background (no scipy dependency).
    dist = np.full(bg.shape, 1e9)
    dist[bg] = 0
    cur = bg.copy()
    for d in range(1, maxdist + 1):
        up = np.zeros_like(cur); up[:-1, :] = cur[1:, :]
        dn = np.zeros_like(cur); dn[1:, :] = cur[:-1, :]
        lf = np.zeros_like(cur); lf[:, :-1] = cur[:, 1:]
        rt = np.zeros_like(cur); rt[:, 1:] = cur[:, :-1]
        grow = (up | dn | lf | rt) & ~cur
        dist[grow & fg] = d
        cur = cur | grow

    rg = R - G
    bgd = B - G
    print(f"  {label}:  bg={bg.sum()}px fg={fg.sum()}px")
    print("     d   n        R-G      B-G   magenta?")
    out = []
    for d in range(1, maxdist + 1):
        m = (dist == d) & fg
        n = int(m.sum())
        if n < 40:
            continue
        a, b = rg[m].mean(), bgd[m].mean()
        mag = "YES" if (a > 1.0 and b > 1.0) else ""
        print(f"    {d:3d} {n:6d}   {a:8.2f} {b:8.2f}   {mag}")
        out.append((d, n, a, b))

    interior = (dist > maxdist) & fg
    if interior.sum() > 200:
        print(f"    INT {int(interior.sum()):6d}   "
              f"{rg[interior].mean():8.2f} {bgd[interior].mean():8.2f}   <- interior control")
    return out


def main():
    targets = [
        ("flower-bud-alone-cpl--SHIP-V2--1to1.png", "flower-bud-alone (reported fringe)"),
        ("bee-3-cpl--SHIP-V2--1to1.png", "bee-3-cpl (NO reported fringe = control)"),
        ("wrapped-text-1--SHIP-V2--1to1.png", "wrapped-text-1 (showcase, no rim = control)"),
    ]
    for fn, label in targets:
        import os
        p = os.path.join(ASSETS, fn)
        if not os.path.exists(p):
            print(f"  {label}: MISSING {p}")
            continue
        profile(p, label)
        print()


if __name__ == "__main__":
    sys.exit(main())
