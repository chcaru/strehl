"""M53 step 1 -- reconcile the shipped high-pass kernel against M41's.

Fact 469's 144.391x was produced by `m41lib.hp_sd(a, w=9)`, which is

    (a - scipy.ndimage.uniform_filter(a, 9)).std()

i.e. a 9x9 box high-pass with scipy's default `mode='reflect'`, with the
residual sd taken over EVERY pixel of the ROI crop including the 4-px border
ring whose window was reflected.

The shipped statistic uses the same 9x9 box but evaluates the residual only
where the whole 9x9 window lies inside the buffer (the "valid interior"),
because that -- and only that -- has the exact closed-form white-noise gain
sqrt(1 - 1/81) that makes the number readable against the calibrated model.

This script measures the difference between the two conventions rather than
arguing about it, on the exact ROI and frame that produced fact 469's
denominator: 109MSDCF, frame index len//2 = 11, plane ROI (1356, 32, 512, 512).
M41's own log records hp_sd = 11.770 DN there, so this is a check against a
published number a human can go and read (rule 35), not against itself.

It also writes the ROI to out/a1_roi_109_mid.f32 so that the Rust side can be
run on byte-identical input.

Read-only corpora are never written.  Rule 32: every rawpy view is copied
inside the `with`.
"""
import os
import sys
import glob
import json

import numpy as np
import rawpy
from scipy.ndimage import uniform_filter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")
os.makedirs(OUT, exist_ok=True)

BLACK = 512.0
W = 9  # box side, M41's default

STACK = r"C:\dev\macro\test\109MSDCF"
ROI = (1356, 32, 512, 512)  # x, y, w, h in plane (quad) coordinates
M41_PUBLISHED_HP_SD = 11.770  # out/a6_run.log line 11, 109MSDCF flat ROI


def quad_green_roi(path, roi):
    """Black-subtracted (G1 + G2) / 2 over an ROI in plane coordinates.

    Identical convention to `strehl-cli`'s `roi_green` and to M41's
    `a2_run.load_two`: RGGB, G1 at (row 0, col 1), G2 at (row 1, col 0).
    """
    x, y, w, h = roi
    with rawpy.imread(path) as r:
        v = r.raw_image_visible
        g1 = v[2 * y:2 * (y + h):2, 2 * x + 1:2 * (x + w) + 1:2].astype(np.float32)
        g2 = v[2 * y + 1:2 * (y + h) + 1:2, 2 * x:2 * (x + w):2].astype(np.float32)
    return 0.5 * (g1 + g2) - BLACK


def hp_sd_m41(a, w=W):
    """M41's exact statistic: reflect borders, sd over the whole ROI."""
    return float((a - uniform_filter(a, w)).std())


def hp_sd_valid(a, w=W):
    """The shipped statistic: residual only where the whole window fits."""
    r = w // 2
    # 'constant' padding is irrelevant here because we discard the border ring;
    # uniform_filter's interior values do not depend on the border mode.
    resid = a - uniform_filter(a, w)
    core = resid[r:a.shape[0] - r, r:a.shape[1] - r]
    return float(core.std())


def main():
    files = sorted(glob.glob(os.path.join(STACK, "*.ARW")))
    mid = len(files) // 2
    print(f"stack        : {STACK}  ({len(files)} frames, middle index {mid})")
    print(f"roi          : x {ROI[0]} y {ROI[1]} w {ROI[2]} h {ROI[3]} (plane coords)")

    a = quad_green_roi(files[mid], ROI)
    assert a.shape == (ROI[3], ROI[2]), a.shape

    raw_sd = float(a.std())
    m41 = hp_sd_m41(a)
    valid = hp_sd_valid(a)

    print()
    print(f"raw spatial sd            : {raw_sd:10.4f} DN   (M41 log: 76.272)")
    print(f"M41 hp_sd  (reflect, full): {m41:10.4f} DN   (M41 log: {M41_PUBLISHED_HP_SD})")
    print(f"M53 hp_sd  (valid interior): {valid:9.4f} DN")
    print(f"M53 / M41                 : {valid / m41:10.6f}x")
    print(f"M41 reproduced to         : {abs(m41 - M41_PUBLISHED_HP_SD) / M41_PUBLISHED_HP_SD * 100:.4f}%"
          f" of the published 11.770")

    # White-noise gain of both conventions, as a control that the difference
    # above is a border effect and not a different kernel.
    rng = np.random.default_rng(20260823)
    sigma = 40.0
    g41, gvd = [], []
    for _ in range(8):
        n = rng.normal(0.0, sigma, size=(512, 512)).astype(np.float32)
        g41.append(hp_sd_m41(n) / sigma)
        gvd.append(hp_sd_valid(n) / sigma)
    theory = float(np.sqrt(1.0 - 1.0 / (W * W)))
    print()
    print(f"white-noise gain, theory  : {theory:.6f}  = sqrt(1 - 1/{W*W})")
    print(f"white-noise gain, M41     : {np.mean(g41):.6f} +- {np.std(g41):.6f}")
    print(f"white-noise gain, M53     : {np.mean(gvd):.6f} +- {np.std(gvd):.6f}")

    path = os.path.join(OUT, "a1_roi_109_mid.f32")
    a.astype("<f4").tofile(path)
    print()
    print(f"wrote {path}  ({ROI[2]}x{ROI[3]} little-endian f32, row-major)")

    with open(os.path.join(OUT, "a1_reconcile.json"), "w") as fh:
        json.dump(dict(stack=STACK, roi=list(ROI), frame=mid, raw_sd=raw_sd,
                       hp_sd_m41=m41, hp_sd_valid=valid,
                       published=M41_PUBLISHED_HP_SD,
                       gain_theory=theory,
                       gain_m41=float(np.mean(g41)),
                       gain_valid=float(np.mean(gvd))), fh, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
