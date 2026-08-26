"""Recover the EXACT flat patch the README's leaf-2-cpl claim measured, and
reproduce its two numbers, so the adjudication is about the claim's own ROI and
not about a ROI of my choosing.

The claim (README "On a whole photograph, measured.", SYNTHESIS fact 1355)
never records its patch coordinates -- `thesis_demo.py` computes them at run
time and prints them. So they are recomputed here by replicating that script's
selection arithmetic byte for byte against the SAME two renders it measured,
which are still on disk. If the two sigmas come back as 0.006381 and 0.000987
the replication is exact and the recovered coordinates are the claim's.

BUILD DISCIPLINE. Those two renders are from commit 925d03d; the pinned
shipping binary is b9b6921e. This file compares the 925d03d renders ONLY
against each other -- a within-build comparison, which is what the claim itself
is -- and never against anything this project rendered later. Every arm
rendered by THIS investigation comes from the pinned binary alone.

WHAT THIS FILE DOES NOT DO. It does not judge the claim. It recovers a
coordinate and reproduces two numbers. The adjudication is `adjudicate.py`.
"""

import pathlib

import numpy as np
import tifffile

ORCH = pathlib.Path(r"C:\dev\strehl-out\ORCH-thesis")
F = 200


def hp_sigma(img, y, x, n=F):
    """thesis_demo.py's statistic, copied exactly: SD of a 3x3 Laplacian
    residual over the RGB mean, normalised by sqrt(20) so white noise of SD s
    reads back s."""
    p = img[y:y + n, x:x + n].mean(axis=2).astype(np.float64)
    lap = (4 * p[1:-1, 1:-1] - p[:-2, 1:-1] - p[2:, 1:-1]
           - p[1:-1, :-2] - p[1:-1, 2:])
    return float(lap.std() / np.sqrt(20.0))


def flat_patch(mean_rgb):
    """thesis_demo.py's ROI search, copied exactly."""
    g = mean_rgb.mean(axis=2)
    s = 16
    gs = g[::s, ::s]
    gx = np.zeros_like(gs)
    gy = np.zeros_like(gs)
    gx[:, 1:-1] = gs[:, 2:] - gs[:, :-2]
    gy[1:-1, :] = gs[2:, :] - gs[:-2, :]
    e = gx * gx + gy * gy
    k = 200 // (2 * s)
    c = np.zeros((e.shape[0] + 1, e.shape[1] + 1))
    np.cumsum(np.cumsum(e.astype(np.float64), 0), 1, out=c[1:, 1:])
    H, W = e.shape
    m = 3 * k
    y0 = np.clip(np.arange(H) - k, 0, H)
    y1 = np.clip(np.arange(H) + k, 0, H)
    x0 = np.clip(np.arange(W) - k, 0, W)
    x1 = np.clip(np.arange(W) + k, 0, W)
    tot = (c[np.ix_(y1, x1)] - c[np.ix_(y0, x1)]
           - c[np.ix_(y1, x0)] + c[np.ix_(y0, x0)])
    tot[:m, :] = np.inf
    tot[-m:, :] = np.inf
    tot[:, :m] = np.inf
    tot[:, -m:] = np.inf
    fy, fx = np.unravel_index(int(np.argmin(tot)), tot.shape)
    return fy * s, fx * s


def recover():
    a = tifffile.imread(ORCH / "leaf-2-cpl-selection-gate0.tif").astype(np.float32) / 65535.0
    b = tifffile.imread(ORCH / "leaf-2-cpl-estimation-gate2.tif").astype(np.float32) / 65535.0
    assert a.shape == b.shape, (a.shape, b.shape)
    fy, fx = flat_patch(0.5 * (a + b))
    sa, sb = hp_sigma(a, fy, fx), hp_sigma(b, fy, fx)
    return {"shape": a.shape, "fy": fy, "fx": fx, "sigma_gate0": sa,
            "sigma_gate2": sb, "ratio": sb / sa, "equiv_frames": (sa / sb) ** 2,
            "mean_gate0": float(a[fy:fy + F, fx:fx + F].mean()),
            "mean_gate2": float(b[fy:fy + F, fx:fx + F].mean())}


if __name__ == "__main__":
    r = recover()
    print(f"render shape (full-res, --srgb, demosaiced) : {r['shape']}")
    print(f"flat patch chosen on the MEAN of both arms  : y={r['fy']} x={r['fx']} ({F}x{F})")
    print()
    print(f"  selection  --gate 0 : sigma {r['sigma_gate0']:.6f}   README says 0.006381")
    print(f"  estimation --gate 2 : sigma {r['sigma_gate2']:.6f}   README says 0.000987")
    print(f"  ratio               : {r['ratio']:.4f}x               README says 0.1546x")
    print(f"  equivalent frames   : {r['equiv_frames']:.2f}         README says 41.8")
    print()
    print(f"  patch mean level    : gate0 {r['mean_gate0']:.5f}  gate2 {r['mean_gate2']:.5f}"
          f"  (ratio {r['mean_gate2'] / r['mean_gate0']:.5f})")
    ok = (abs(r["sigma_gate0"] - 0.006381) < 5e-6 and abs(r["sigma_gate2"] - 0.000987) < 5e-6)
    print()
    print("REPLICATION EXACT -- the recovered patch is the claim's."
          if ok else "REPLICATION FAILED -- do not use these coordinates.")
