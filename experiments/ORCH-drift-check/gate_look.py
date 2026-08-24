"""G3/G4/G5 for the pinned gate ablation.

G5 (negative control): flat-ROI sigma MUST rise monotonically as the gate falls.
    The measured ladder predicts sigma gain 0.6273x at gate 4.00 against
    1.0000x at gate 0.00 -- i.e. gate 0 should be ~1.594x noisier than gate 4.
    If measured noise does NOT rise, the instrument is not seeing the gate and
    G3/G4 mean nothing.

G3 (sharpness, by eye): 1:1 crops, no post, on a high-detail region.
G4 (veil, by eye): 1:1 crops on the silhouette region where facts 1371-1372
    recorded a bright veil hugging the subject outline, invariant across all
    three resampler kernels (fact 1375).
"""
import io
import os

import numpy as np
import tifffile

OUT = r"C:\dev\strehl-out\ORCH-gate"
GATES = ["4.00", "2.00", "0.7078", "0.00"]


def load(g):
    return tifffile.imread(os.path.join(OUT, f"pin-bee-3-cpl-gate-{g}.tif"))


def main():
    a = load("4.00")
    print("shape", a.shape, "dtype", a.dtype, "min", a.min(), "max", a.max())

    # luminance, coarse, to locate flat background and high-detail regions
    lum = a.astype(np.float32).mean(axis=2)
    H, W = lum.shape
    B = 128
    hb, wb = H // B, W // B
    tiles = lum[: hb * B, : wb * B].reshape(hb, B, wb, B).swapaxes(1, 2)
    # local detail = SD of the Laplacian-ish first difference within each tile
    gx = np.abs(np.diff(tiles, axis=3)).mean(axis=(2, 3))
    tile_mean = tiles.mean(axis=(2, 3))

    flat_idx = np.unravel_index(np.argmin(gx + (tile_mean < np.percentile(tile_mean, 60)) * 1e6), gx.shape)
    det_idx = np.unravel_index(np.argmax(gx), gx.shape)
    print(f"flattest tile  {flat_idx}  gx={gx[flat_idx]:.4f} mean={tile_mean[flat_idx]:.0f}")
    print(f"detailed tile  {det_idx}   gx={gx[det_idx]:.4f} mean={tile_mean[det_idx]:.0f}")

    fy, fx = flat_idx[0] * B, flat_idx[1] * B
    dy, dx = det_idx[0] * B, det_idx[1] * B

    # ---------------- G5 ----------------
    print("\n=== G5  flat-ROI noise (must RISE as gate falls) ===")
    print(f"ROI: y={fy}..{fy+B}, x={fx}..{fx+B}  (flattest 128px tile in the upper 40% of levels)")
    print(f"{'gate':>8} {'mean':>10} {'sigma':>10} {'rel to g4':>10}   predicted")
    pred = {"4.00": 0.6273, "2.00": 0.6974, "0.7078": 0.7810 * 0.95, "0.00": 1.0000}
    sig = {}
    for g in GATES:
        img = load(g)
        roi = img[fy:fy + B, fx:fx + B].astype(np.float64)
        # per-channel sigma after removing a plane, then averaged: a residual
        # gradient in the ROI would otherwise be counted as noise
        s = []
        yy, xx = np.mgrid[0:B, 0:B]
        A = np.stack([np.ones(B * B), yy.ravel(), xx.ravel()], axis=1)
        for c in range(3):
            v = roi[:, :, c].ravel()
            coef, *_ = np.linalg.lstsq(A, v, rcond=None)
            s.append((v - A @ coef).std())
        sig[g] = float(np.mean(s))
    for g in GATES:
        print(f"{g:>8} {load(g)[fy:fy+B, fx:fx+B].mean():>10.1f} {sig[g]:>10.2f}"
              f" {sig[g]/sig['4.00']:>10.3f}   {pred[g]/pred['4.00']:.3f}x")

    order = [sig[g] for g in GATES]  # gate descending 4 -> 0
    rising = all(order[i] < order[i + 1] for i in range(len(order) - 1))
    print("G5", "PASS -- noise rises monotonically as the gate falls" if rising
          else "FAIL -- noise did not rise; instrument is not seeing the gate")

    # ---------------- G3 / G4 crops ----------------
    def montage(y, x, side, zoom, name, label):
        cols = []
        for g in GATES:
            img = load(g)
            c = img[y:y + side, x:x + side]
            c8 = (c.astype(np.float32) / 257.0).clip(0, 255).astype(np.uint8)
            if zoom > 1:
                c8 = np.repeat(np.repeat(c8, zoom, axis=0), zoom, axis=1)
            cols.append(c8)
        gap = 12
        h, w = cols[0].shape[:2]
        out = np.full((h, w * len(cols) + gap * (len(cols) - 1), 3), 255, np.uint8)
        for i, c in enumerate(cols):
            out[:, i * (w + gap):i * (w + gap) + w] = c
        import PIL.Image
        PIL.Image.fromarray(out).save(os.path.join(OUT, name))
        print(f"wrote {name}  {out.shape}  [{label}]  order: {' | '.join('gate '+g for g in GATES)}")

    montage(dy - 100, dx - 100, 340, 2, "G3-SHARPNESS.png", "high-detail, x2 zoom")
    montage(3150, 700, 700, 1, "G4-VEIL.png", "silhouette / veil region, 1:1")
    print("\nMontage column order (left to right):", ", ".join("gate " + g for g in GATES))


if __name__ == "__main__":
    main()
