"""K1 failed. Diagnose it, then replace it with a control that is actually valid.

Pre-registered K1 said: a scene band-limited below the binned Nyquist must put
`var(D)` at the noise floor. It read **6.47x** the floor instead.

That is not an instrument fault. It is an error in my specification of the
control, and the algebra says so. For a plane wave at (fy, fx) in full-res
cycles/px sampled at the G1 and G2 sites, whose offset is (-1, +1) full-res px:

    D = (G1 - G2)/2  ->  |D| = |A| * |sin(pi (fx - fy))|

`sin` is zero only on the main diagonal fx = fy and at DC. **Any** off-diagonal
content produces a non-zero D, at every frequency, not only above the Nyquist.
`mean(G1,G2)` has the complementary transfer `cos(pi (fx - fy))`, so binning's
attenuation of green begins immediately and reaches a **complete null** at the
anti-diagonal Nyquist corner. K1 as written asserted something algebraically
false.

The valid control is a band-limit ladder: var(D)/noise must be monotone in the
scene's band limit and must approach 1 as the band limit approaches 0. This file
runs it, and checks the closed-form prediction against the measurement.
"""

import json
import os
import sys

import numpy as np

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")
BLACK = 512.0

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from s1_measure import bandlimited, bandpass, quincunx, shoot, vard, planes  # noqa: E402


def predicted_ratio(fmax, n=768, amp=600.0, pedestal=2500.0, gain=2.5):
    """Closed form: mean of sin^2(pi(fx-fy)) over the disc r <= fmax, times the
    scene variance, over the noise variance in D. No fitting, no free parameter."""
    fy = np.fft.fftfreq(n)[:, None] * np.ones((1, n))
    fx = np.fft.fftfreq(n)[None, :] * np.ones((n, 1))
    m = np.hypot(fy, fx) <= fmax
    m[0, 0] = False
    if not m.any():
        return 1.0
    s2 = float(np.mean(np.sin(np.pi * (fx[m] - fy[m])) ** 2))
    noise = pedestal * gain / 2.0
    return (amp * amp * s2 + noise) / noise


def main():
    rng = np.random.default_rng(7717)
    res = {}

    print("== K1' corrected: band-limit ladder, with a closed-form prediction ==")
    print("   %-8s %10s %10s %8s %10s" % ("fmax", "varD", "noise", "ratio", "predicted"))
    ladder = []
    for fmax in (0.005, 0.01, 0.02, 0.05, 0.10, 0.15, 0.20, 0.25):
        scene = bandlimited(rng, 768, fmax)
        g1, g2 = quincunx(shoot(rng, scene))
        f1, f2 = quincunx(shoot(rng, np.zeros((768, 768))))
        v, nz = vard(0.5 * (g1 - g2)), vard(0.5 * (f1 - f2))
        pr = predicted_ratio(fmax)
        ladder.append({"fmax": fmax, "varD": v, "noise": nz, "ratio": v / nz, "pred": pr})
        print("   %-8.3f %10.1f %10.1f %8.3f %10.3f" % (fmax, v, nz, v / nz, pr))
    res["K1prime"] = ladder
    ratios = [r["ratio"] for r in ladder]
    mono = all(ratios[i] <= ratios[i + 1] * 1.02 for i in range(len(ratios) - 1))
    err = max(abs(r["ratio"] - r["pred"]) / r["pred"] for r in ladder)
    print("   monotone in band limit : %s" % mono)
    print("   floor at fmax=0.005    : %.4f  (must approach 1)" % ratios[0])
    print("   worst deviation from the closed form : %.1f %%" % (100 * err))
    res["K1prime_monotone"] = bool(mono)
    res["K1prime_floor"] = ratios[0]
    res["K1prime_worst_pred_err_pct"] = 100 * err

    # ------------------------------------------------------------------------
    # What the headline actually needs: is the extra D in a focused frame in the
    # part of the band the binned grid CANNOT represent, or merely the part it
    # attenuates? Split D's own spectrum at the binned half-Nyquist.
    # ------------------------------------------------------------------------
    print("\n== spectral split of D on the real frames ==")
    z = np.load(os.path.join(OUT, "tiles.npz"))
    s1 = json.load(open(os.path.join(OUT, "s1_measure.json"), encoding="utf-8"))
    split = {}
    for key in sorted(k for k in z.files if k.startswith("T")):
        info = s1["tiles"][key]
        out = {}
        for tag in ("sharp", "soft"):
            i = info[tag]["i"]
            s, d = planes(z[key][i])
            d = d - d.mean()
            w = np.hanning(d.shape[0])[:, None] * np.hanning(d.shape[1])[None, :]
            P = np.abs(np.fft.fft2(d * w)) ** 2
            fy = np.fft.fftfreq(d.shape[0])[:, None]
            fx = np.fft.fftfreq(d.shape[1])[None, :]
            r = np.hypot(fy, fx)                       # binned cyc/px
            out[tag] = {
                "low": float(P[r <= 0.25].sum()),      # binned grid represents easily
                "high": float(P[r > 0.25].sum()),      # upper half of the binned band
                "total": float(P.sum()),
            }
        eh = out["sharp"]["high"] / out["soft"]["high"]
        el = out["sharp"]["low"] / out["soft"]["low"]
        split[key] = {"sharp": out["sharp"], "soft": out["soft"],
                      "E_high": eh, "E_low": el}
        print("   %s  E(upper half of D's band) %6.3f   E(lower half) %6.3f"
              % (key, eh, el))
    res["spectral_split"] = split

    with open(os.path.join(OUT, "s2_controls.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
