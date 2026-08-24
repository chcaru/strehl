"""Does the capture carry green detail that binning destroys?

`mean(G1,G2)` is what the binned render keeps. `(G1-G2)/2` is, algebraically and
exactly, what it annihilates: for samples offset by `d` binned px the mean has
transfer `cos(pi f.d)` and the half-difference `i sin(pi f.d)`, and the two are
complementary. G1 and G2 are offset by (-0.5, +0.5) binned px, so the mean has a
null at the anti-diagonal Nyquist corner and the difference has its maximum there.

Nothing here interpolates. D is built from raw photosites.
"""

import json
import os
import sys

import numpy as np

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")
BLACK = 512.0


def planes(stack):
    """stack: (2, h, w) uint16 -> S (kept by binning), D (destroyed by binning)."""
    g1 = stack[0].astype(np.float64) - BLACK
    g2 = stack[1].astype(np.float64) - BLACK
    return 0.5 * (g1 + g2), 0.5 * (g1 - g2)


def gradmag(a):
    gy, gx = np.gradient(a)
    return float(np.sqrt(gy * gy + gx * gx).mean())


def vard(d):
    """Variance of D with its own mean removed.

    The mean removal matters: a fixed G1/G2 sensitivity difference is a pedestal
    on D and would otherwise be counted as detail. It is identical in both frames
    of a pair anyway, but removing it makes that independent of the argument.
    """
    return float(np.var(d - d.mean()))


# ---------------------------------------------------------------- synthetic --
def quincunx(scene):
    """Sample a full-res scene at the G1 and G2 photosite positions."""
    return scene[0::2, 1::2], scene[1::2, 0::2]


def bandlimited(rng, n, fmax_fullres, amp=600.0):
    """White noise low-passed to a disc of radius `fmax_fullres` cyc/full-res px."""
    x = rng.standard_normal((n, n))
    F = np.fft.fft2(x)
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.fftfreq(n)[None, :]
    F[np.hypot(fy, fx) > fmax_fullres] = 0
    y = np.real(np.fft.ifft2(F))
    return amp * y / (y.std() + 1e-12)


def bandpass(rng, n, lo, hi, amp=600.0):
    x = rng.standard_normal((n, n))
    F = np.fft.fft2(x)
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.fftfreq(n)[None, :]
    r = np.hypot(fy, fx)
    F[(r < lo) | (r > hi)] = 0
    y = np.real(np.fft.ifft2(F))
    return amp * y / (y.std() + 1e-12)


def shoot(rng, scene, pedestal=2500.0, gain=2.5):
    """Add Poisson shot noise at a realistic level for this sensor."""
    lam = np.clip((scene + pedestal) / gain, 1e-6, None)
    return rng.poisson(lam).astype(np.float64) * gain


def synth_case(rng, scene_fn, n=768, reps=5):
    out = []
    for _ in range(reps):
        scene = scene_fn(rng, n)
        noisy = shoot(rng, scene)
        g1, g2 = quincunx(noisy)
        d = 0.5 * (g1 - g2)
        s = 0.5 * (g1 + g2)
        # noise-only reference: the same pedestal with no scene at all
        flat = shoot(rng, np.zeros((n, n)))
        f1, f2 = quincunx(flat)
        out.append((vard(d), vard(0.5 * (f1 - f2)), gradmag(s)))
    return out


def main():
    z = np.load(os.path.join(OUT, "tiles.npz"))
    names = [str(x) for x in z["names"]]
    meta = json.load(open(os.path.join(OUT, "tiles_meta.json"), encoding="utf-8"))
    res = {"meta": meta, "tiles": {}, "controls": {}}
    rng = np.random.default_rng(20260824)

    # ------------------------------------------------------------ headline --
    print("== headline: same photosites, in focus vs defocused ==")
    for key in sorted(k for k in z.files if k.startswith("T")):
        arr = z[key]
        rows = []
        for i in range(arr.shape[0]):
            s, d = planes(arr[i])
            rows.append({"i": i, "name": names[i], "mean": float(s.mean()),
                         "grad": gradmag(s), "vard": vard(d), "vars": float(np.var(s))})
        sharp = max(rows, key=lambda r: r["grad"])
        # Match brightness: shot-noise variance rides on signal level, so the
        # defocused partner is chosen from frames within 10 % of the sharp
        # frame's mean. Without this the comparison confounds noise with detail.
        cand = [r for r in rows if abs(r["mean"] - sharp["mean"]) / sharp["mean"] < 0.10]
        soft = min(cand, key=lambda r: r["grad"])
        E = sharp["vard"] / soft["vard"]
        # shot-noise-normalised variant, in case the 10 % window still matters
        En = (sharp["vard"] / sharp["mean"]) / (soft["vard"] / soft["mean"])
        res["tiles"][key] = {"rows": rows, "sharp": sharp, "soft": soft,
                             "E": E, "E_shotnorm": En,
                             "n_candidates": len(cand),
                             "frac_var_in_D": sharp["vard"] / (sharp["vard"] + sharp["vars"])}
        print("  %s sharp %s grad %6.2f varD %9.1f | soft %s grad %6.2f varD %9.1f"
              % (key, sharp["name"], sharp["grad"], sharp["vard"],
                 soft["name"], soft["grad"], soft["vard"]))
        print("       mean %.0f vs %.0f (%d candidates in the 10%% window)   E = %.3f   E_shotnorm = %.3f"
              % (sharp["mean"], soft["mean"], len(cand), E, En))

    # ------------------------------------------------------------- K4 null --
    print("\n== K4 null: a frame against itself ==")
    k4 = []
    for key in sorted(k for k in z.files if k.startswith("T")):
        i = res["tiles"][key]["sharp"]["i"]
        _, d = planes(z[key][i])
        k4.append(vard(d) / vard(d))
    res["controls"]["K4"] = k4
    print("   E = %s  (must be exactly 1)" % set("%.6f" % v for v in k4))

    # ------------------------------------------ K1 specificity, K2 sensitivity --
    print("\n== K1 specificity: scene band-limited well below the binned Nyquist ==")
    k1 = synth_case(rng, lambda r, n: bandlimited(r, n, 0.10))
    res["controls"]["K1"] = k1
    for v, f, g in k1:
        print("   varD %9.1f   noise-only %9.1f   ratio %6.3f" % (v, f, v / f))
    k1r = [v / f for v, f, _ in k1]

    print("\n== K2 sensitivity: scene with energy at the anti-diagonal Nyquist ==")
    k2 = synth_case(rng, lambda r, n: bandpass(r, n, 0.20, 0.25))
    res["controls"]["K2"] = k2
    for v, f, g in k2:
        print("   varD %9.1f   noise-only %9.1f   ratio %6.3f" % (v, f, v / f))
    k2r = [v / f for v, f, _ in k2]

    print("\n   K1 ratio mean %.3f   K2 ratio mean %.3f   separation %.1fx"
          % (np.mean(k1r), np.mean(k2r), np.mean(k2r) / np.mean(k1r)))
    res["controls"]["K1_mean"] = float(np.mean(k1r))
    res["controls"]["K2_mean"] = float(np.mean(k2r))

    # -------------------------------------------------- K3 physical dose --
    print("\n== K3 dose-response: varD against the real focus sweep ==")
    k3 = {}
    for key in sorted(k for k in z.files if k.startswith("T")):
        rows = res["tiles"][key]["rows"]
        gi = int(np.argmax([r["grad"] for r in rows]))
        vi = int(np.argmax([r["vard"] for r in rows]))
        gr = np.array([r["grad"] for r in rows])
        vd = np.array([r["vard"] for r in rows])
        corr = float(np.corrcoef(gr, vd)[0, 1])
        k3[key] = {"argmax_grad": gi, "argmax_vard": vi, "offset": vi - gi, "corr": corr}
        print("   %s  peak of grad(S) at frame %2d, peak of var(D) at %2d  (offset %+d)  corr %.3f"
              % (key, gi, vi, vi - gi, corr))
    res["controls"]["K3"] = k3

    with open(os.path.join(OUT, "s1_measure.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
