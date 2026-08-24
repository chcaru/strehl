"""Noise-free green signal spectrum, with an UNBIASED cross-spectral estimator.

s5 failed two of its own controls and I am replacing it rather than reporting it.

  * **V1 failed**: `|Sxy|` on two independent noise fields read 0.18, not 0. That
    is not a bug, it is bias -- a magnitude is non-negative, so averaging `|Sxy|`
    over a 9x9 frequency neighbourhood leaves a floor of order 1/sqrt(81).
    A magnitude can never be an unbiased estimator of shared power.
  * **V3 failed**: the least-squares phase-slope read 0.75-0.78 against a planted
    1.0, because phase wraps at high frequency and the weighting did not protect
    against it.

Both are fixed by the same change: **de-ramp first, then take the real part.**
G1 and G2 are offset by a known d = (-0.5, +0.5) binned px, so

    P_sig(f) = Re( <G1* G2> exp(-i 2 pi f . d) )

is real, positive for shared content, and **zero-mean for independent noise** --
so it is unbiased. And the geometry check becomes a scan: the shift that
maximises the de-ramped real part must be the true one.

The perceptual question also needs a different statistic. 0.3 % of total power
is true and useless: green power is dominated by low frequencies where binning's
attenuation is nil. Sharpness lives in the top of the band, so the destroyed
fraction is reported **per band** as well as overall.
"""

import json
import os
import sys

import numpy as np
import tifffile
from scipy.ndimage import uniform_filter

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")
REN = r"C:\dev\strehl-out\M95-resolution"
BLACK = 512.0
SMOOTH = 9
D_G1_TO_G2 = (0.5, -0.5)          # (dv, du) binned px, from the RGGB geometry


def grids(n):
    fv = np.fft.fftfreq(n)[:, None] * np.ones((1, n))
    fu = np.fft.fftfreq(n)[None, :] * np.ones((n, 1))
    return fu, fv


def cross(g1, g2, smooth=SMOOTH):
    n = g1.shape[0]
    w = np.hanning(n)[:, None] * np.hanning(n)[None, :]
    A = np.fft.fft2((g1 - g1.mean()) * w)
    B = np.fft.fft2((g2 - g2.mean()) * w)
    sm = lambda a: uniform_filter(a, smooth, mode="wrap")
    C = np.conj(A) * B
    return sm(np.abs(A) ** 2), sm(np.abs(B) ** 2), sm(C.real) + 1j * sm(C.imag)


def signal_power(g1, g2, d=D_G1_TO_G2):
    """Unbiased shared-power spectrum: de-ramp by the known offset, take Re."""
    n = g1.shape[0]
    Sxx, Syy, Sxy = cross(g1, g2)
    fu, fv = grids(n)
    ramp = np.exp(-2j * np.pi * (fv * d[0] + fu * d[1]))
    P = (Sxy * ramp).real
    N = np.maximum((Sxx + Syy) / 2 - P, 0)
    return P, N, (fu, fv)


def report(g1, g2):
    P, N, (fu, fv) = signal_power(g1, g2)
    t = np.pi * 0.5 * (fu - fv)
    lose_w, keep_w = np.sin(t) ** 2, np.cos(t) ** 2
    r = np.hypot(fu, fv)
    m = np.ones_like(P, dtype=bool)
    m[0, 0] = False
    Pc = np.clip(P, 0, None)          # negative bins are noise, not signal

    def frac(sel):
        s = m & sel
        tot = (Pc[s] * (lose_w[s] + keep_w[s])).sum()
        return float((Pc[s] * lose_w[s]).sum() / tot) if tot > 0 else 0.0

    return {
        "destroyed_all": frac(np.ones_like(P, dtype=bool)),
        "destroyed_top_octave": frac(r >= 0.25),
        "destroyed_upper_half": frac(r >= 0.125),
        "signal": float(Pc[m].sum()),
        "noise": float(N[m].sum()),
        "snr": float(Pc[m].sum() / max(N[m].sum(), 1e-9)),
    }


def controls():
    rng = np.random.default_rng(9091)
    n = 384
    out = {}

    print("== V1' null: two independent noise fields (UNBIASED estimator) ==")
    a = rng.standard_normal((n, n)) * 50 + 2000
    b = rng.standard_normal((n, n)) * 50 + 2000
    P, _, _ = signal_power(a, b, d=(0.0, 0.0))
    Sxx, Syy, _ = cross(a, b)
    v1 = float(P.sum() / ((Sxx + Syy).sum() / 2))
    print("   shared/total = %+.5f   (unbiased: must straddle 0)" % v1)
    out["V1"] = v1

    print("\n== V2' positive: one scene seen twice, independent noise ==")
    sc = rng.standard_normal((n, n))
    F = np.fft.fft2(sc)
    fu, fv = grids(n)
    F[np.hypot(fu, fv) > 0.2] = 0
    sc = 300 * np.real(np.fft.ifft2(F))
    a = sc + rng.standard_normal((n, n)) * 50 + 2000
    b = sc + rng.standard_normal((n, n)) * 50 + 2000
    P, _, _ = signal_power(a, b, d=(0.0, 0.0))
    Sxx, Syy, _ = cross(a, b)
    v2 = float(P.sum() / ((Sxx + Syy).sum() / 2))
    print("   shared/total = %+.5f   (must be near 1)" % v2)
    print("   separation V2'/|V1'| = %.0fx" % (abs(v2 / v1) if v1 else float("inf")))
    out["V2"] = v2

    print("\n== V3' geometry: scan the offset, the peak must land on the planted one ==")
    rows = []
    for planted in (0.5, 0.25, -0.25, 0.0):
        S = np.fft.fft2(sc)
        fy, fx = np.fft.fftfreq(n)[:, None], np.fft.fftfreq(n)[None, :]
        sh = np.real(np.fft.ifft2(S * np.exp(-2j * np.pi * (fy * -planted + fx * planted))))
        aa = sc + rng.standard_normal((n, n)) * 50 + 2000
        bb = sh + rng.standard_normal((n, n)) * 50 + 2000
        best, bd = -1e30, None
        for cand in np.arange(-0.75, 0.7501, 0.05):
            P, _, _ = signal_power(aa, bb, d=(cand, -cand))
            s = P.sum()
            if s > best:
                best, bd = s, cand
        rows.append({"planted": planted, "recovered": round(float(bd), 4)})
        print("   planted %+.2f -> recovered %+.2f  %s"
              % (planted, bd, "OK" if abs(bd - planted) < 0.051 else "FAIL"))
    out["V3"] = rows
    out["V3_ok"] = all(abs(r["recovered"] - r["planted"]) < 0.051 for r in rows)
    return out


def geometry_scan(g1, g2):
    """Recover the G1->G2 offset from the data alone.

    Nothing is assumed: the scan reports the offset that maximises shared power.
    If it lands on (+0.5, -0.5) that is the RGGB quad geometry measured, not
    derived, and it independently confirms the sign used everywhere above.
    """
    best, bd = -1e30, None
    for cand in np.arange(-0.75, 0.7501, 0.05):
        P, _, _ = signal_power(g1, g2, d=(cand, -cand))
        s = P.sum()
        if s > best:
            best, bd = s, float(cand)
    return bd


def main():
    res = {"controls": controls()}
    meta = json.load(open(os.path.join(OUT, "tiles_meta.json"), encoding="utf-8"))
    z = np.load(os.path.join(OUT, "tiles.npz"))
    s1 = json.load(open(os.path.join(OUT, "s1_measure.json"), encoding="utf-8"))
    T = meta["tile"]

    for tag, src in (("render", "demo-align.tif"), ("render_noalign", "demo-noalign.tif")):
        img = tifffile.imread(os.path.join(REN, src))
        g1p = img[:, :, 1].astype(np.float64)[0::2, 1::2]
        g2p = img[:, :, 1].astype(np.float64)[1::2, 0::2]
        print("\n== merged render, %s ==" % src)
        res[tag] = {}
        for key, (by, bx) in meta["tiles"].items():
            r = report(g1p[by:by + T, bx:bx + T], g2p[by:by + T, bx:bx + T])
            res[tag][key] = r
            print("   %s  destroyed: all %5.2f %% | upper half %5.1f %% | top octave %5.1f %% | SNR %6.1f"
                  % (key, 100 * r["destroyed_all"], 100 * r["destroyed_upper_half"],
                     100 * r["destroyed_top_octave"], r["snr"]))

    print("\n== sharpest single raw frame ==")
    res["raw"] = {}
    for key in sorted(k for k in z.files if k.startswith("T")):
        i = s1["tiles"][key]["sharp"]["i"]
        r = report(z[key][i][0].astype(np.float64) - BLACK,
                   z[key][i][1].astype(np.float64) - BLACK)
        res["raw"][key] = r
        print("   %s  destroyed: all %5.2f %% | upper half %5.1f %% | top octave %5.1f %% | SNR %6.1f"
              % (key, 100 * r["destroyed_all"], 100 * r["destroyed_upper_half"],
                 100 * r["destroyed_top_octave"], r["snr"]))

    print("\n== V4: recover the G1->G2 offset from the DATA, no geometry assumed ==")
    res["geometry"] = {}
    for key in sorted(k for k in z.files if k.startswith("T")):
        i = s1["tiles"][key]["sharp"]["i"]
        raw = geometry_scan(z[key][i][0].astype(np.float64) - BLACK,
                            z[key][i][1].astype(np.float64) - BLACK)
        res["geometry"][key] = raw
        print("   %s raw frame -> d = (%+.2f, %+.2f) binned px   (RGGB predicts (+0.50, -0.50))"
              % (key, raw, -raw))
    ok = all(abs(v - 0.5) < 0.051 for v in res["geometry"].values())
    res["geometry_ok"] = bool(ok)
    print("   all four tiles land on the predicted quad geometry: %s" % ok)

    with open(os.path.join(OUT, "s6_signal.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
