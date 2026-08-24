"""M111 step 0 -- audit ORCH's blob probe BEFORE building on it.

ORCH's `blob_probe.py` compares a strehl render against a LibRaw single-frame
control by cropping both to the common top-left rectangle and reading the SAME
(x, y) in each.  That is only valid if the two arms are registered to each other
and carry commensurable tone.  Neither was checked.  This script checks both,
because if either fails, ORCH's cross-arm ratio (0.094 vs 0.761) is measuring
the offset rather than the merge.

Three questions, each answerable with a number:

  A1  Are the arms REGISTERED?  Phase-correlate a grid of high-variance tiles
      from the merged arm against the control.  A consistent non-zero shift
      means "the same (x, y)" is not the same scene point.
  A2  Is the TONE commensurable?  Fit merged luma against control luma on the
      matched (shifted) grid; report the slope and the correlation.  A gradient
      ratio between arms is meaningless if one arm's transfer curve is steeper
      where the mask is drawn.
  A3  Is the blob CLIPPED?  Report the fraction of blob-interior pixels at or
      near the 16-bit container top in each arm, and the luma means.

Usage:  python audit_probe.py
"""

import os
import sys

import numpy as np
import tifffile

OUT = r"C:\dev\strehl-out\ORCH-thennow"
MERGED = os.path.join(OUT, "marker-HEAD-8f46f04.tif")
CTRL = os.path.join(OUT, "CONTROL-singleframe-dry-erase-marker-head-cpl.tif")

# ORCH's two blobs, verbatim from blob_probe.py.
ZOOMS = [
    ("blobA-row4", 4715, 1180, 300, 260),
    ("blobB-row2", 2048, 1300, 320, 300),
]


def luma(a):
    a = a.astype(np.float32)
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def phase_shift(a, b):
    """Integer (dy, dx) that best aligns b onto a, by phase correlation."""
    a = a - a.mean()
    b = b - b.mean()
    win = np.outer(np.hanning(a.shape[0]), np.hanning(a.shape[1]))
    fa = np.fft.rfft2(a * win)
    fb = np.fft.rfft2(b * win)
    cross = fa * np.conj(fb)
    mag = np.abs(cross)
    mag[mag == 0] = 1e-12
    r = np.fft.irfft2(cross / mag, s=a.shape)
    peak = np.unravel_index(np.argmax(r), r.shape)
    dy = peak[0] if peak[0] <= a.shape[0] // 2 else peak[0] - a.shape[0]
    dx = peak[1] if peak[1] <= a.shape[1] // 2 else peak[1] - a.shape[1]
    return int(dy), int(dx), float(r[peak])


def main():
    m = tifffile.imread(MERGED)
    c = tifffile.imread(CTRL)
    print(f"merged shape {m.shape} dtype {m.dtype}")
    print(f"control shape {c.shape} dtype {c.dtype}")
    h, w = min(m.shape[0], c.shape[0]), min(m.shape[1], c.shape[1])
    mc, cc = m[:h, :w], c[:h, :w]
    ym, yc = luma(mc), luma(cc)
    print(f"common crop {h}x{w}   luma mean merged {ym.mean():.1f} control {yc.mean():.1f} "
          f"ratio {ym.mean() / yc.mean():.4f}")

    # ---- A1: registration -------------------------------------------------
    print("\n--- A1  REGISTRATION (phase correlation, 512px tiles) ---")
    t = 512
    ys = np.linspace(400, h - t - 400, 4).astype(int)
    xs = np.linspace(400, w - t - 400, 5).astype(int)
    shifts = []
    print("   tile(y,x)        var(merged)     dy    dx    peak")
    for y0 in ys:
        for x0 in xs:
            am = ym[y0:y0 + t, x0:x0 + t]
            ac = yc[y0:y0 + t, x0:x0 + t]
            v = float(am.var())
            dy, dx, pk = phase_shift(am, ac)
            shifts.append((v, dy, dx, pk, y0, x0))
            print(f"   ({y0:5d},{x0:5d})  {v:12.3e}  {dy:5d} {dx:5d}  {pk:.4f}")
    strong = [s for s in shifts if s[0] > np.median([q[0] for q in shifts])]
    dys = np.array([s[1] for s in strong])
    dxs = np.array([s[2] for s in strong])
    print(f"   high-variance tiles n={len(strong)}  dy median {np.median(dys):.1f} "
          f"(sd {dys.std():.1f})   dx median {np.median(dxs):.1f} (sd {dxs.std():.1f})")

    # ---- A2: tone ----------------------------------------------------------
    print("\n--- A2  TONE COMMENSURABILITY ---")
    dy0, dx0 = int(np.median(dys)), int(np.median(dxs))
    print(f"   applying the measured shift (dy={dy0}, dx={dx0}) to the control")
    sy = slice(max(0, dy0), h + min(0, dy0))
    sx = slice(max(0, dx0), w + min(0, dx0))
    ty = slice(max(0, -dy0), h + min(0, -dy0))
    tx = slice(max(0, -dx0), w + min(0, -dx0))
    a = ym[sy, sx][::8, ::8].ravel()
    b = yc[ty, tx][::8, ::8].ravel()
    n = min(a.size, b.size)
    a, b = a[:n], b[:n]
    r = float(np.corrcoef(a, b)[0, 1])
    slope = float(np.polyfit(b, a, 1)[0])
    print(f"   matched samples {n}   pearson r {r:.4f}   slope merged~control {slope:.4f}")
    for lo, hi in [(0, 16000), (16000, 32000), (32000, 48000), (48000, 60000), (60000, 65536)]:
        sel = (b >= lo) & (b < hi)
        if sel.sum() > 500:
            print(f"     control luma [{lo:5d},{hi:5d})  n={sel.sum():8d}  "
                  f"merged mean {a[sel].mean():8.1f}  local slope "
                  f"{np.polyfit(b[sel], a[sel], 1)[0]:7.3f}")

    # ---- A3: is the blob clipped? -----------------------------------------
    print("\n--- A3  BLOB INTERIORS: level and clipping ---")
    for name, x, y, bw, bh in ZOOMS:
        mm = mc[y:y + bh, x:x + bw]
        cc2 = cc[y:y + bh, x:x + bw]
        yl = luma(mm)
        thr = np.percentile(yl, 75)
        mask = yl >= thr
        print(f"   [{name}] merged luma mean {yl.mean():8.1f}  blob-mask mean {yl[mask].mean():8.1f}")
        for label, arr in (("merged", mm), ("control", cc2)):
            top = (arr >= 65000).any(axis=2)
            allc = (arr >= 65000).all(axis=2)
            print(f"      {label:8s}  any-channel >=65000: {100 * top.mean():6.3f}%   "
                  f"all >=65000: {100 * allc.mean():6.3f}%   "
                  f"luma mean {luma(arr).mean():8.1f}  p99 {np.percentile(luma(arr), 99):8.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
