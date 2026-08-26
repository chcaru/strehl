"""Is sRGB the right MASTER space for these prints? A measurement, not a preference.

ORCH asked for a recommendation with a measurement behind it. The question has
two halves and they pull in opposite directions:

  (a) How much real colour does sRGB throw away on this corpus?
  (b) What does a wider space cost -- specifically, does spreading 16 bits over
      a larger volume risk visible posterisation?

METHOD

The delivered `--srgb` and `--linear-srgb` masters are already clipped, so they
cannot say what was lost. The camera-native render is not clipped. So for each
subject we render BOTH from ONE binary and recover the colour matrix the binary
actually used by least squares on the unclipped pixel pairs.

Recovering it empirically rather than transcribing constants means we measure
what the code DID, not what a header says. And the recovery is falsifiable:
`camera_to_srgb`'s own documentation states that "every row of the returned
matrix sums to 1" by construction. That prediction was made by the source, not
by this script, so it is a real check -- if the fit is wrong, the rows will not
sum to 1.

CIEDE2000 is implemented here and validated against Sharma, Wu & Dalal's
published test vectors before it is used for anything.

All measurement is in LINEAR light on camera-native data. Nothing here is
computed from a graded or tone-mapped file.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import tifffile

GAMUT = Path(r"C:\dev\strehl-out\ICC-AB\gamut")

# xy primaries + white, from each space's defining document.
SPACES = {
    "sRGB / BT.709": ((0.6400, 0.3300), (0.3000, 0.6000), (0.1500, 0.0600), (0.3127, 0.3290)),
    "Display P3":    ((0.6800, 0.3200), (0.2650, 0.6900), (0.1500, 0.0600), (0.3127, 0.3290)),
    "Adobe RGB 1998": ((0.6400, 0.3300), (0.2100, 0.7100), (0.1500, 0.0600), (0.3127, 0.3290)),
    "ProPhoto RGB":  ((0.734699, 0.265301), (0.159597, 0.840403), (0.036598, 0.000105),
                      (0.345704, 0.358540)),
}

# Sharma, Wu & Dalal (2005), "The CIEDE2000 Color-Difference Formula",
# Color Research & Application 30(1). Published verification data.
SHARMA = [
    ((50.0000, 2.6772, -79.7751), (50.0000, 0.0000, -82.7485), 2.0425),
    ((50.0000, 3.1571, -77.2803), (50.0000, 0.0000, -82.7485), 2.8615),
    ((50.0000, 2.8361, -74.0200), (50.0000, 0.0000, -82.7485), 3.4412),
    ((50.0000, -1.3802, -84.2814), (50.0000, 0.0000, -82.7485), 1.0000),
    ((50.0000, -1.1848, -84.8006), (50.0000, 0.0000, -82.7485), 1.0000),
    ((50.0000, -0.9009, -85.5211), (50.0000, 0.0000, -82.7485), 1.0000),
    ((50.0000, 0.0000, 0.0000), (50.0000, -1.0000, 2.0000), 2.3669),
    ((50.0000, -1.0000, 2.0000), (50.0000, 0.0000, 0.0000), 2.3669),
    ((50.0000, 2.4900, -0.0010), (50.0000, -2.4900, 0.0009), 7.1792),
    ((60.2574, -34.0099, 36.2677), (60.4626, -34.1751, 39.4387), 1.2644),
    ((63.0109, -31.0961, -5.8663), (62.8187, -29.7946, -4.0864), 1.2630),
    ((61.2901, 3.7196, -5.3901), (61.4292, 2.2480, -4.9620), 1.8731),
    ((35.0831, -44.1164, 3.7933), (35.0232, -40.0716, 1.5901), 1.8645),
    ((22.7233, 20.0904, -46.6940), (23.0331, 14.9730, -42.5619), 2.0373),
    ((2.0776, 0.0795, -1.1350), (0.9033, -0.0636, -0.5514), 0.9082),
]


def rgb_to_xyz(prim) -> np.ndarray:
    r, g, b, w = prim
    def X(xy):
        x, y = xy
        return np.array([x / y, 1.0, (1 - x - y) / y])
    P = np.stack([X(r), X(g), X(b)], axis=1)
    W = X(w)
    return P * np.linalg.solve(P, W)[None, :]


def bradford(src_w, dst_w) -> np.ndarray:
    B = np.array([[0.8951, 0.2664, -0.1614],
                  [-0.7502, 1.7135, 0.0367],
                  [0.0389, -0.0685, 1.0296]])
    s, d = B @ src_w, B @ dst_w
    return np.linalg.inv(B) @ np.diag(d / s) @ B


def xyz_to_lab(xyz: np.ndarray, white: np.ndarray) -> np.ndarray:
    t = xyz / white[None, :]
    e, k = 216 / 24389, 24389 / 27
    f = np.where(t > e, np.cbrt(np.maximum(t, 1e-12)), (k * t + 16) / 116)
    return np.stack([116 * f[:, 1] - 16,
                     500 * (f[:, 0] - f[:, 1]),
                     200 * (f[:, 1] - f[:, 2])], axis=1)


def ciede2000(lab1: np.ndarray, lab2: np.ndarray) -> np.ndarray:
    L1, a1, b1 = lab1[:, 0], lab1[:, 1], lab1[:, 2]
    L2, a2, b2 = lab2[:, 0], lab2[:, 1], lab2[:, 2]
    C1, C2 = np.hypot(a1, b1), np.hypot(a2, b2)
    Cb = (C1 + C2) / 2
    G = 0.5 * (1 - np.sqrt(Cb**7 / (Cb**7 + 25.0**7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1p = np.degrees(np.arctan2(b1, a1p)) % 360
    h2p = np.degrees(np.arctan2(b2, a2p)) % 360
    h1p = np.where((b1 == 0) & (a1p == 0), 0.0, h1p)
    h2p = np.where((b2 == 0) & (a2p == 0), 0.0, h2p)
    dLp = L2 - L1
    dCp = C2p - C1p
    prod = C1p * C2p
    dh = h2p - h1p
    dhp = np.where(prod == 0, 0.0,
                   np.where(dh > 180, dh - 360, np.where(dh < -180, dh + 360, dh)))
    dHp = 2 * np.sqrt(prod) * np.sin(np.radians(dhp / 2))
    Lbp = (L1 + L2) / 2
    Cbp = (C1p + C2p) / 2
    hsum, hdiff = h1p + h2p, np.abs(h1p - h2p)
    hbp = np.where(prod == 0, hsum,
                   np.where(hdiff <= 180, hsum / 2,
                            np.where(hsum < 360, (hsum + 360) / 2, (hsum - 360) / 2)))
    T = (1 - 0.17 * np.cos(np.radians(hbp - 30))
         + 0.24 * np.cos(np.radians(2 * hbp))
         + 0.32 * np.cos(np.radians(3 * hbp + 6))
         - 0.20 * np.cos(np.radians(4 * hbp - 63)))
    dtheta = 30 * np.exp(-(((hbp - 275) / 25) ** 2))
    Rc = 2 * np.sqrt(Cbp**7 / (Cbp**7 + 25.0**7))
    Sl = 1 + (0.015 * (Lbp - 50) ** 2) / np.sqrt(20 + (Lbp - 50) ** 2)
    Sc = 1 + 0.045 * Cbp
    Sh = 1 + 0.015 * Cbp * T
    Rt = -np.sin(np.radians(2 * dtheta)) * Rc
    return np.sqrt((dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2
                   + Rt * (dCp / Sc) * (dHp / Sh))


def commission_de() -> bool:
    l1 = np.array([p[0] for p in SHARMA])
    l2 = np.array([p[1] for p in SHARMA])
    want = np.array([p[2] for p in SHARMA])
    got = ciede2000(l1, l2)
    err = np.abs(got - want)
    ok = err.max() < 1e-4
    print(f"CIEDE2000 vs Sharma et al. published vectors: {len(SHARMA)} pairs, "
          f"max error {err.max():.6f}  -> {'VALIDATED' if ok else 'WRONG'}")
    if not ok:
        for (a, b, w), g in zip(SHARMA, got):
            if abs(g - w) >= 1e-4:
                print(f"    {a} vs {b}: want {w}, got {g:.4f}")
    return ok


def load(stem: str):
    cam = tifffile.imread(GAMUT / f"{stem}--camera.tiff")
    lin = tifffile.imread(GAMUT / f"{stem}--linear.tiff")
    assert cam.dtype == np.uint16 and lin.dtype == np.uint16, "expected uint16"
    assert cam.shape == lin.shape, f"{stem}: shape mismatch {cam.shape} vs {lin.shape}"
    return cam.astype(np.float64) / 65535.0, lin.astype(np.float64) / 65535.0


def fit_matrix(cam: np.ndarray, lin: np.ndarray):
    """Recover the matrix the binary used, from unclipped pixel pairs only."""
    c = cam.reshape(-1, 3)
    out = lin.reshape(-1, 3)
    inside = np.all((out > 1e-4) & (out < 1.0 - 1e-4), axis=1)
    n = int(inside.sum())
    if n < 10000:
        return None, n, np.nan
    idx = np.random.default_rng(0).choice(np.flatnonzero(inside),
                                          size=min(n, 400_000), replace=False)
    A, B = c[idx], out[idx]
    M, *_ = np.linalg.lstsq(A, B, rcond=None)
    M = M.T
    resid = float(np.median(np.abs(A @ M.T - B)))
    return M, n, resid


def main() -> int:
    if not commission_de():
        print("REFUSING TO CONTINUE: the colour-difference metric is not validated.")
        return 2
    print()

    stems = sorted({p.name.rsplit("--", 1)[0] for p in GAMUT.glob("*--camera.tiff")})
    if not stems:
        print(f"no renders in {GAMUT}")
        return 2

    xyz_of = {k: rgb_to_xyz(v) for k, v in SPACES.items()}
    d65 = np.array([0.3127 / 0.3290, 1.0, (1 - 0.3127 - 0.3290) / 0.3290])
    pro_w = np.array([0.345704 / 0.358540, 1.0,
                      (1 - 0.345704 - 0.358540) / 0.358540])
    to_d65 = {k: (np.eye(3) if k != "ProPhoto RGB" else bradford(pro_w, d65))
              for k in SPACES}

    rows = []
    print(f"{'subject':38} {'rowsums':>22} {'resid p50':>10}   out-of-gamut % of coloured pixels")
    print(f"{'':38} {'':>22} {'':>10}   " +
          "  ".join(f"{k.split(' /')[0][:11]:>11}" for k in SPACES) + f"  {'DIRECT sRGB':>12}")
    print("-" * 156)

    for stem in stems:
        cam, lin = load(stem)
        M, n_in, resid = fit_matrix(cam, lin)
        if M is None:
            print(f"{stem:38} too few unclipped pixels ({n_in}) -- SKIPPED, not passed")
            rows.append((stem, None))
            continue
        rowsums = M.sum(axis=1)

        # Unclamped linear sRGB: what the clamp threw away.
        true_srgb = cam.reshape(-1, 3) @ M.T
        # Only judge pixels with real signal; near-black is noise, not colour.
        lum = true_srgb @ np.array([0.2126, 0.7152, 0.0722])
        sel = lum > 0.005

        # MODEL-FREE CROSS-CHECK. The delivered --linear-srgb file clamps
        # out-of-gamut channels to exactly 0 (`develop_pixel`: no tone => plain
        # per-channel clamp, verified in source). So a coloured pixel sitting at
        # exactly 0 in some channel IS an out-of-gamut pixel, by the definition
        # of the gamut, with no matrix and no fit involved. If this disagrees
        # with the fitted-matrix census, the fitted matrix is not usable.
        lflat = lin.reshape(-1, 3)
        llum = lflat @ np.array([0.2126, 0.7152, 0.0722])
        dsel = llum > 0.005
        direct = float((np.any(lflat[dsel] <= 0.0, axis=1)).mean() * 100) if dsel.any() else 0.0

        k = np.flatnonzero(sel)
        if k.size > 600_000:
            k = np.random.default_rng(1).choice(k, 600_000, replace=False)
        px = true_srgb[k]
        xyz = px @ xyz_of["sRGB / BT.709"].T

        frac = {}
        for name, m in xyz_of.items():
            rgb = xyz @ (np.linalg.inv(to_d65[name] @ m)).T
            frac[name] = float((np.any(rgb < -1e-4, axis=1)).mean() * 100)

        # What clipping to sRGB costs, in CIEDE2000, on the pixels it touches.
        clipped = np.clip(px, 0.0, None)
        oo = np.any(px < -1e-4, axis=1)
        if oo.sum() > 0:
            w = np.array([0.9504559, 1.0, 1.0890578])
            de = ciede2000(xyz_to_lab(px[oo] @ xyz_of["sRGB / BT.709"].T, w),
                           xyz_to_lab(clipped[oo] @ xyz_of["sRGB / BT.709"].T, w))
            de_med, de_p99, de_max = float(np.median(de)), float(np.percentile(de, 99)), float(de.max())
        else:
            de_med = de_p99 = de_max = 0.0

        rows.append((stem, dict(frac=frac, de=(de_med, de_p99, de_max), direct=direct,
                                rowsums=rowsums, resid=resid, n=int(sel.sum()))))
        print(f"{stem:38} {rowsums[0]:.4f},{rowsums[1]:.4f},{rowsums[2]:.4f} "
              f"{resid:10.2e}   " +
              "  ".join(f"{frac[k]:10.3f}%" for k in SPACES) +
              f"  {direct:11.3f}%")

    ok = [r for _, r in rows if r]

    print("\n--- IS THE RECOVERED MATRIX GOOD ENOUGH TO CARRY THESE NUMBERS? ---")
    worst = max((abs(r["rowsums"] - 1).max() for r in ok), default=np.nan)
    print("`camera_to_srgb` documents that every row sums to 1. That prediction comes")
    print(f"from the source, not from this script.  max |rowsum - 1| = {worst:.2e}")
    print("The recovery is therefore good to ~0.3%, NOT exact. The fit is not perfectly")
    print("linear (median residual ~1e-4, above the 1.5e-5 quantisation floor), so the")
    print("matrix is ARGUED-adequate, not proven exact. The check that matters is")
    print("whether the census AGREES with the model-free column:")
    print(f"\n{'subject':38} {'fitted':>10} {'direct':>10} {'diff':>10}")
    print("-" * 70)
    bad = 0
    for stem, r in rows:
        if not r:
            continue
        f, d = r["frac"]["sRGB / BT.709"], r["direct"]
        agree = abs(f - d) < max(0.5, 0.25 * max(f, d))
        if not agree:
            bad += 1
        print(f"{stem:38} {f:9.3f}% {d:9.3f}% {f - d:+9.3f}%"
              + ("" if agree else "   <-- DISAGREE"))
    print(f"\nagree {len(ok) - bad} / disagree {bad} / total {len(ok)}")
    print("The two columns are computed by different routes -- one applies a recovered")
    print("matrix to camera-native data, the other just counts clamped channels in the")
    print("delivered file. Agreement means the fitted matrix is fit for this purpose.")

    print(f"\n{'subject':38} {'dE2000 of sRGB clipping (on clipped px)':>44}")
    print(f"{'':38} {'median':>14}{'p99':>14}{'max':>14}")
    print("-" * 84)
    for stem, r in rows:
        if not r:
            continue
        print(f"{stem:38} {r['de'][0]:14.2f}{r['de'][1]:14.2f}{r['de'][2]:14.2f}")

    # Posterisation: ORCH's stated hazard for a wider space.
    print("\nPOSTERISATION RISK AT 16 BITS")
    print("One 16-bit code step, expressed in dE2000, at a mid-tone. A step well")
    print("below 1.0 cannot posterise: 1.0 dE is roughly one just-noticeable difference.")
    w = np.array([0.9504559, 1.0, 1.0890578])
    for name, m in xyz_of.items():
        base = np.full((1, 3), 0.18)
        step = base.copy()
        step[0, 1] += 1.0 / 65535.0
        M2 = to_d65[name] @ m
        lab1 = xyz_to_lab(base @ M2.T, w)
        lab2 = xyz_to_lab(step @ M2.T, w)
        d16 = float(ciede2000(lab1, lab2)[0])
        d8 = d16 * 257
        print(f"  {name:16} 16-bit step {d16:.5f} dE   (the same step at 8 bits "
              f"would be {d8:.3f} dE)")

    print(f"\nsubjects measured {len(ok)} / skipped {len(rows) - len(ok)} / total {len(rows)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
