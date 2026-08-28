"""magtruth.py -- ground-truth commissioning of magdose.magnify().

magdose.py claims `magnify(plane, D)` displaces a feature at radius r outward by
D*1e-6*r px. Everything downstream depends on that claim, and it has so far only
been checked against the very estimator it is supposed to commission -- which is
circular. This checks the dose against GEOMETRY instead: Gaussian blobs at known
radii, centroid measured before and after, compared with the closed form.

A centroid is exact for a symmetric blob under a locally-affine resample, so the
expected error is the interpolator's, not the statistic's. If this arm does not
return the planted dose, every ppm figure derived from magdose is wrong.
"""
from __future__ import annotations

import numpy as np

from magdose import magnify

N = 2001
C = (N - 1) / 2.0
RADII = [200.0, 500.0, 800.0]
SIGMA = 6.0


def blob_image(radii):
    img = np.zeros((N, N), dtype=np.float32)
    yy, xx = np.mgrid[0:N, 0:N]
    for r in radii:
        for cy, cx in ((C, C + r), (C + r, C), (C - r * 0.6, C + r * 0.8)):
            img += np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * SIGMA ** 2)))
    return img.astype(np.float32)


def centroid(img, cy, cx, half=20):
    y0, y1 = int(cy - half), int(cy + half + 1)
    x0, x1 = int(cx - half), int(cx + half + 1)
    sub = img[y0:y1, x0:x1].astype(np.float64)
    sub = np.clip(sub, 0, None)
    yy, xx = np.mgrid[y0:y1, x0:x1]
    s = sub.sum()
    return (yy * sub).sum() / s, (xx * sub).sum() / s


def main():
    sites = []
    for r in RADII:
        sites += [(C, C + r, r), (C + r, C, r), (C - r * 0.6, C + r * 0.8, r)]
    img = blob_image(RADII)

    print("dose(ppm)   radius   expected_px   measured_px    error_px   ratio")
    print("---------------------------------------------------------------------")
    for D in (0.0, 200.0, 704.5, 1000.0, 5000.0):
        out = magnify(img, D)
        ratios = []
        for (cy, cx, r) in sites:
            by, bx = centroid(img, cy, cx)
            ay, ax = centroid(out, cy, cx)
            # radial component of the measured centroid motion
            uy, ux = (by - C) / r, (bx - C) / r
            meas = (ay - by) * uy + (ax - bx) * ux
            exp = D * 1e-6 * r
            err = meas - exp
            ratio = meas / exp if exp != 0 else float("nan")
            ratios.append(ratio)
            print(f"{D:9.1f} {r:8.0f} {exp:13.4f} {meas:13.4f} {err:11.4f}"
                  f" {ratio:7.4f}")
        if D != 0.0:
            print(f"{'':9s} {'mean ratio':>8s} {'':13s} {'':13s} {'':11s}"
                  f" {np.mean(ratios):7.4f}")
        print()


if __name__ == "__main__":
    main()
