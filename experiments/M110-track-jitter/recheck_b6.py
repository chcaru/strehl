"""Re-evaluate B6's comparison on the current binary.

B6's conclusion is a RELATIVE claim between two arms. The archived TIFFs were
rendered at 12:57/12:58 on a binary that no longer exists (rebuilt 13:06, and
other agents have since changed `merge_cmd.rs`). This recomputes the same
shift-invariant scalars on a contemporaneous pair rendered back-to-back on the
current binary, so the conclusion is re-tested rather than assumed.

Shift-invariant scalars only: turning the prior on moves the whole frame by
~0.57 px, so a difference image measures the gauge shift, not the jitter.
"""

import hashlib
import sys

import numpy as np
import tifffile

A_PATH = r"C:\dev\strehl-out\M110\ctl\rA.tif"
B_PATH = r"C:\dev\strehl-out\M110\ctl\r1.tif"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def luma(img):
    a = np.asarray(img, dtype=np.float64)
    if a.ndim == 3 and a.shape[2] >= 3:
        return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
    return a if a.ndim == 2 else a.reshape(a.shape[0], -1)


def highband(y):
    """Energy above the resampler's own passband: y minus a 3x3 box blur."""
    k = np.ones((3, 3), dtype=np.float64) / 9.0
    pad = np.pad(y, 1, mode="edge")
    blur = np.zeros_like(y)
    for i in range(3):
        for j in range(3):
            blur += k[i, j] * pad[i : i + y.shape[0], j : j + y.shape[1]]
    d = y - blur
    return float(np.mean(d * d))


def phase_shift(a, b):
    """Integer global shift of b relative to a, by phase correlation."""
    n = 1024
    ay, ax = a.shape[0] // 2 - n // 2, a.shape[1] // 2 - n // 2
    wa = a[ay : ay + n, ax : ax + n]
    wb = b[ay : ay + n, ax : ax + n]
    wa = wa - wa.mean()
    wb = wb - wb.mean()
    win = np.outer(np.hanning(n), np.hanning(n))
    FA = np.fft.rfft2(wa * win)
    FB = np.fft.rfft2(wb * win)
    R = FA * np.conj(FB)
    mag = np.abs(R)
    mag[mag == 0] = 1.0
    corr = np.fft.irfft2(R / mag, s=(n, n))
    peak = np.unravel_index(np.argmax(corr), corr.shape)
    dy = peak[0] if peak[0] < n // 2 else peak[0] - n
    dx = peak[1] if peak[1] < n // 2 else peak[1] - n
    return dy, dx


def main():
    print(f"A  {A_PATH}\n   sha256 {sha256(A_PATH)}")
    print(f"B  {B_PATH}\n   sha256 {sha256(B_PATH)}")

    a_img = tifffile.imread(A_PATH)
    b_img = tifffile.imread(B_PATH)
    print(f"shape {a_img.shape} dtype {a_img.dtype}")
    if a_img.shape != b_img.shape:
        sys.exit("shape mismatch -- arms are not comparable")

    ya, yb = luma(a_img), luma(b_img)
    print(f"byte-identical            : {sha256(A_PATH) == sha256(B_PATH)}")

    dy, dx = phase_shift(ya, yb)
    print(f"integer global shift (B-A): dy={dy} dx={dx} px")

    h, w = ya.shape
    cy, cx = h // 2, w // 2
    r = 512
    ca = ya[cy - r : cy + r, cx - r : cx + r]
    cb = yb[cy - r : cy + r, cx - r : cx + r]

    for name, pa, pb in (("centre 1024x1024", ca, cb), ("whole frame", ya, yb)):
        ea, eb = highband(pa), highband(pb)
        pct = 100.0 * (eb - ea) / ea if ea else float("nan")
        print(f"high-band energy {name:<18}: A={ea:.6g}  B={eb:.6g}  B-A={pct:+.3f}%")


if __name__ == "__main__":
    main()
