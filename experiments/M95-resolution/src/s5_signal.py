"""The noise-free number: what fraction of the green SIGNAL does binning destroy?

The raw high-band power ratio is not admissible -- the P1 background control in
s4 read 7.73x on a crop with no subject in it, which is noise, not detail. This
file removes the noise instead of arguing about it.

G1 and G2 lie on the same binned grid, offset by (-0.5, +0.5) binned px, and
their noise is independent because they are different photosites. So with
X(f) the scene and the spectra smoothed over a frequency neighbourhood:

    Sxy = <G1* G2> = |X|^2 exp(i 2 pi f . (p2 - p1))    (noise decorrelates)
    |mean|^2 = |X|^2 cos^2(pi f . (p1 - p2))            (what binning keeps)
    |diff|^2 = |X|^2 sin^2(pi f . (p1 - p2))            (what binning destroys)

f . (p1 - p2) = 0.5 (fu - fv) in cycles per binned px, so binning green has a
**complete null** at the anti-diagonal Nyquist corner and full transmission
along the main diagonal. The destroyed fraction is a weighted sum over the
measured, noise-free |X|^2.

The phase of Sxy is a free internal check: it must equal -pi (fu - fv) from the
geometry alone. Nothing is fitted to make that true.
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


def spectra(g1, g2, smooth=SMOOTH):
    n = g1.shape[0]
    w = np.hanning(n)[:, None] * np.hanning(n)[None, :]
    A = np.fft.fft2((g1 - g1.mean()) * w)
    B = np.fft.fft2((g2 - g2.mean()) * w)
    sm = lambda a: uniform_filter(a, smooth, mode="wrap")
    Sxx = sm(np.abs(A) ** 2)
    Syy = sm(np.abs(B) ** 2)
    Sxy = sm(np.real(np.conj(A) * B)) + 1j * sm(np.imag(np.conj(A) * B))
    return Sxx, Syy, Sxy


def grids(n):
    fv = np.fft.fftfreq(n)[:, None] * np.ones((1, n))
    fu = np.fft.fftfreq(n)[None, :] * np.ones((n, 1))
    return fu, fv


def destroyed_fraction(g1, g2):
    n = g1.shape[0]
    Sxx, Syy, Sxy = spectra(g1, g2)
    fu, fv = grids(n)
    t = np.pi * 0.5 * (fu - fv)
    sig = np.abs(Sxy)                      # noise-free signal power
    noise = np.maximum((Sxx + Syy) / 2 - sig, 0)
    keep = sig * np.cos(t) ** 2
    lose = sig * np.sin(t) ** 2
    m = np.ones_like(sig, dtype=bool)
    m[0, 0] = False
    # phase check, weighted by signal power so it is dominated by real content
    pred = -2 * t
    err = np.angle(np.exp(1j * (np.angle(Sxy) - pred)))
    wsum = sig[m].sum()
    return {
        "destroyed_fraction": float(lose[m].sum() / (keep[m].sum() + lose[m].sum())),
        "signal_power": float(sig[m].sum()),
        "noise_power": float(noise[m].sum()),
        "snr": float(sig[m].sum() / max(noise[m].sum(), 1e-9)),
        "phase_err_deg": float(np.degrees(np.abs(err * sig)[m].sum() / wsum)),
    }


# ------------------------------------------------------------------ controls --
def controls():
    rng = np.random.default_rng(4242)
    n = 384
    print("== V1 null: two independent noise fields, no scene ==")
    a = rng.standard_normal((n, n)) * 50 + 2000
    b = rng.standard_normal((n, n)) * 50 + 2000
    Sxx, Syy, Sxy = spectra(a, b)
    r = float(np.abs(Sxy).sum() / ((Sxx + Syy).sum() / 2))
    print("   signal/total = %.4f   (must be near 0: nothing is shared)" % r)

    print("\n== V2 positive: one scene seen twice with independent noise ==")
    scene = rng.standard_normal((n, n))
    F = np.fft.fft2(scene)
    fu, fv = grids(n)
    F[np.hypot(fu, fv) > 0.2] = 0
    scene = 300 * np.real(np.fft.ifft2(F))
    a = scene + rng.standard_normal((n, n)) * 50 + 2000
    b = scene + rng.standard_normal((n, n)) * 50 + 2000
    Sxx, Syy, Sxy = spectra(a, b)
    r2 = float(np.abs(Sxy).sum() / ((Sxx + Syy).sum() / 2))
    print("   signal/total = %.4f   (must be near 1: the scene is shared)" % r2)
    print("   separation V2/V1 = %.1fx" % (r2 / r))

    print("\n== V3 geometry: plant a KNOWN sub-pixel offset, read it back ==")
    rows = []
    for planted in (0.5, 0.25, -0.25):
        fy, fx = np.fft.fftfreq(n)[:, None], np.fft.fftfreq(n)[None, :]
        S = np.fft.fft2(scene)
        # shift b by (-planted, +planted) binned px, the G1->G2 geometry
        sh = np.real(np.fft.ifft2(S * np.exp(-2j * np.pi * (fy * -planted + fx * planted))))
        aa = scene + rng.standard_normal((n, n)) * 50 + 2000
        bb = sh + rng.standard_normal((n, n)) * 50 + 2000
        _, _, Sxy = spectra(aa, bb)
        fu, fv = grids(n)
        t = np.pi * planted * (fu - fv)
        w = np.abs(Sxy)
        w[0, 0] = 0
        # least-squares slope of measured phase against the predicted ramp
        num = float((w * np.angle(Sxy) * (-2 * t)).sum())
        den = float((w * (2 * t) ** 2).sum())
        rows.append((planted, num / den if den else 0.0))
        print("   planted %+.2f binned px -> recovered scale %.4f (must be 1.0)"
              % (planted, num / den if den else 0.0))
    return {"V1": r, "V2": r2, "V3": rows}


def main():
    res = {"controls": controls()}
    meta = json.load(open(os.path.join(OUT, "tiles_meta.json"), encoding="utf-8"))
    z = np.load(os.path.join(OUT, "tiles.npz"))
    s1 = json.load(open(os.path.join(OUT, "s1_measure.json"), encoding="utf-8"))
    T = meta["tile"]

    print("\n== the merged render (linear, aligned, --demosaic) ==")
    img = tifffile.imread(os.path.join(REN, "demo-align.tif"))
    green = img[:, :, 1].astype(np.float64)
    g1p, g2p = green[0::2, 1::2], green[1::2, 0::2]
    res["render"] = {}
    for key, (by, bx) in meta["tiles"].items():
        g1 = g1p[by:by + T, bx:bx + T]
        g2 = g2p[by:by + T, bx:bx + T]
        r = destroyed_fraction(g1, g2)
        res["render"][key] = r
        print("   %s destroyed %.1f %% of green signal power | SNR %6.1f | phase err %.2f deg"
              % (key, 100 * r["destroyed_fraction"], r["snr"], r["phase_err_deg"]))

    print("\n== the sharpest single raw frame, same tiles ==")
    res["raw"] = {}
    for key in sorted(k for k in z.files if k.startswith("T")):
        i = s1["tiles"][key]["sharp"]["i"]
        g1 = z[key][i][0].astype(np.float64) - BLACK
        g2 = z[key][i][1].astype(np.float64) - BLACK
        r = destroyed_fraction(g1, g2)
        res["raw"][key] = r
        print("   %s destroyed %.1f %% of green signal power | SNR %6.1f | phase err %.2f deg"
              % (key, 100 * r["destroyed_fraction"], r["snr"], r["phase_err_deg"]))

    with open(os.path.join(OUT, "s5_signal.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
