"""M120 step 2b — registration by FFT phase correlation, wide search.

Step 2's integer search returned an ENDPOINT (dy=24, dx=-24 on a +/-24 window)
with a flat correlation surface, which per AGENTS rule 13 is "no optimum found
within the sweep", not an offset. This does the whole-plane version: high-pass
both arms, phase-correlate over the full box, and report the peak, its
sharpness, and the runner-up so the claim can be refused.
"""

import sys
from pathlib import Path

import numpy as np
import tifffile
from scipy import ndimage as ndi

M87 = Path(r"C:\dev\blog\death-of-software\projects\strehl\experiments\M87-occlusion\cache")
OUT = Path(r"C:\dev\strehl-out\M120")
OUT.mkdir(parents=True, exist_ok=True)

ROI = (1200, 1900, 300, 1400)
MARGIN = 22
BOX = (ROI[0] - MARGIN, ROI[1] + MARGIN, ROI[2] - MARGIN, ROI[3] + MARGIN)


def highpass(a, sigma=3.0):
    a = a.astype(np.float32)
    return a - ndi.gaussian_filter(a, sigma)


def phase_corr(ref, mov):
    """Return (dy, dx) such that mov[y+dy, x+dx] ~ ref[y, x], plus peak stats."""
    F = np.fft.rfft2(ref)
    G = np.fft.rfft2(mov)
    R = F * np.conj(G)
    R /= np.maximum(np.abs(R), 1e-12)
    c = np.fft.irfft2(R, s=ref.shape)
    idx = int(np.argmax(c))
    py, px = np.unravel_index(idx, c.shape)
    peak = float(c[py, px])
    cc = c.copy()
    y0 = max(py - 3, 0)
    x0 = max(px - 3, 0)
    cc[y0 : py + 4, x0 : px + 4] = -1
    second = float(cc.max())
    dy = py if py < ref.shape[0] // 2 else py - ref.shape[0]
    dx = px if px < ref.shape[1] // 2 else px - ref.shape[1]
    return (-dy, -dx), peak, second


def main() -> int:
    sel = np.load(M87 / "bee3-leg-sel.npy").astype(np.float32)
    ship = tifffile.imread(M87 / "ship-before-linear.tif")[:, :, 1].astype(np.float32)
    h, w = sel.shape

    # Take a window from the shipped plane at the nominal (identity) position
    # padded generously, then phase-correlate equal-sized crops.
    pad = 256
    y0, x0 = BOX[0] - pad, BOX[2] - pad
    win = ship[y0 : y0 + h + 2 * pad, x0 : x0 + w + 2 * pad]
    ref = np.zeros_like(win)
    ref[pad : pad + h, pad : pad + w] = sel

    a = highpass(ref)
    b = highpass(win)
    a *= np.hanning(a.shape[0])[:, None] * np.hanning(a.shape[1])[None, :]
    b *= np.hanning(b.shape[0])[:, None] * np.hanning(b.shape[1])[None, :]

    (dy, dx), peak, second = phase_corr(a, b)
    print(f"phase correlation: shift (dy={dy}, dx={dx})  peak={peak:.5f}  runner-up={second:.5f}"
          f"  ratio={peak / max(second, 1e-9):.2f}x")

    # Verify by direct NCC at the reported offset and its neighbours.
    def ncc_at(oy, ox):
        m = ship[BOX[0] + oy : BOX[0] + oy + h, BOX[2] + ox : BOX[2] + ox + w]
        if m.shape != sel.shape:
            return float("nan")
        p = highpass(sel)
        q = highpass(m)
        p -= p.mean()
        q -= q.mean()
        return float((p * q).sum() / np.sqrt((p * p).sum() * (q * q).sum()))

    base = ncc_at(dy, dx)
    print(f"high-pass NCC at reported offset: {base:.5f}")
    for oy, ox in ((0, 0), (dy + 4, dx), (dy - 4, dx), (dy, dx + 4), (dy, dx - 4),
                   (dy + 16, dx), (dy, dx + 16)):
        print(f"    NCC at (dy={oy:+d}, dx={ox:+d}) = {ncc_at(oy, ox):.5f}")

    np.save(OUT / "pc1_offset.npy", np.array([dy, dx]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
