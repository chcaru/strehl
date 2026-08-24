"""Is the tool's printed 'pred sigma gain (model)' column wrong, or am I
measuring a different quantity from the one it predicts?

The flat ROI measured 33.5x from gate 4.00 to gate 0.00; the printed model
predicts 1.594x. Before naming that a defect I must check the obvious benign
explanation: the printed number may be an IMAGE-WIDE average, in which case it
is diluted by the 38.77% (at gate 4) to 100% (at gate 0) of pixels that use one
frame regardless and therefore cannot change at all.

Three ROIs, chosen to span the leverage axis, plus an image-wide estimate.
"""
import os

import numpy as np
import tifffile

OUT = r"C:\dev\strehl-out\ORCH-gate"
GATES = ["4.00", "2.00", "0.7078", "0.00"]
PRED = {"4.00": 0.6273, "2.00": 0.6974, "0.7078": 0.7810, "0.00": 1.0000}


def load(g):
    return tifffile.imread(os.path.join(OUT, f"pin-bee-3-cpl-gate-{g}.tif"))


def plane_sigma(roi):
    h, w = roi.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    A = np.stack([np.ones(h * w), yy.ravel(), xx.ravel()], axis=1)
    out = []
    for c in range(3):
        v = roi[:, :, c].astype(np.float64).ravel()
        coef, *_ = np.linalg.lstsq(A, v, rcond=None)
        out.append((v - A @ coef).std())
    return float(np.mean(out))


def main():
    imgs = {g: load(g) for g in GATES}
    a = imgs["4.00"]
    lum = a.astype(np.float32).mean(axis=2)
    H, W = lum.shape

    B = 128
    hb, wb = H // B, W // B
    tiles = lum[: hb * B, : wb * B].reshape(hb, B, wb, B).swapaxes(1, 2)
    gx = np.abs(np.diff(tiles, axis=3)).mean(axis=(2, 3))

    flat = np.unravel_index(np.argsort(gx, axis=None)[0], gx.shape)
    mid = np.unravel_index(np.argsort(gx, axis=None)[gx.size // 2], gx.shape)
    det = np.unravel_index(np.argsort(gx, axis=None)[-1], gx.shape)

    print(f"{'ROI':>12} {'tile gx':>10} " + " ".join(f"{'g'+g:>9}" for g in GATES) + "   ratio 4->0   model")
    for name, idx in (("flattest", flat), ("median", mid), ("most detail", det)):
        y, x = idx[0] * B, idx[1] * B
        sig = {g: plane_sigma(imgs[g][y:y + B, x:x + B]) for g in GATES}
        r = sig["0.00"] / sig["4.00"]
        print(f"{name:>12} {gx[idx]:>10.1f} " + " ".join(f"{sig[g]:>9.1f}" for g in GATES)
              + f"   {r:>9.2f}x   {PRED['0.00']/PRED['4.00']:.3f}x")

    # image-wide: high-pass SD over a decimated grid, which is what an
    # image-wide 'sigma gain' would most plausibly mean
    print()
    step = 7
    base = None
    for g in GATES:
        v = imgs[g][::step, ::step, 1].astype(np.float64)
        hp = v[1:-1, 1:-1] - 0.25 * (v[:-2, 1:-1] + v[2:, 1:-1] + v[1:-1, :-2] + v[1:-1, 2:])
        s = float(np.median(np.abs(hp)) * 1.4826)
        if base is None:
            base = s
        print(f"image-wide (decimated) gate {g:>7}: robust HP sigma {s:9.2f}   rel {s/base:6.3f}x"
              f"   model {PRED[g]/PRED['4.00']:.3f}x")


if __name__ == "__main__":
    main()
