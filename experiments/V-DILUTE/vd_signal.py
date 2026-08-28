# -*- coding: utf-8 -*-
"""V-DILUTE: how much TRUE scene signal does 112MSDCF carry, per band?

WHY THIS FILE EXISTS. `vd_band2.py` compared the mean of N real frames against
the mean of N twin frames and I described it as a sensitivity test. It is not:
the twin is built as `base + noise` where `base` IS the real mean, so the twin
carries the same signal PLUS extra noise and the ratio is bounded above by 1 by
construction. It could never show "real > twin" no matter how much signal was
present. That is a degenerate gauge and it is repaired here rather than quietly
reused.

WHAT THE ALGEBRA ACTUALLY GIVES, which is stronger than what was intended.
Let S be the TRUE scene power in a band and y the residual noise power left
after averaging N frames (y = sigma^2 / N). Then

    real_mean power  =  S + y
    twin_mean power  =  S + y + y  =  S + 2y        (independent noise added)
    rm = (S + y) / (S + 2y)

which inverts to a direct estimate of scene signal in units of the post-average
noise floor:

    S / y  =  (2*rm - 1) / (1 - rm)

rm -> 1 means signal-dominated; rm -> 0.5 means S = 0, i.e. the band is empty
of scene content even after averaging N frames. This is a far sharper question
than "is a single frame above its noise floor", and it is the question that
decides whether a sharpness statistic in that band is measuring the picture or
the grain.

COMMISSIONED IN BOTH DIRECTIONS: a planted sinusoid of known power must be
recovered at the right band and must NOT appear in the others; and a pure-noise
input must estimate S/y ~ 0.
"""
import io
import json
import os
import sys

import numpy as np

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                              errors="replace")

BUNDLE = r"C:\dev\strehl-out\V-NEVERWORSE\bundle"
OUT = r"D:\strehl-out\V-DILUTE\premium"
EDGES = [0.10, 0.13, 0.17, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50]


def load(subj):
    z = np.load(os.path.join(BUNDLE, "%s.npz" % subj))
    meta = json.load(io.open(os.path.join(BUNDLE, "%s.json" % subj),
                             encoding="utf-8"))
    ok = {r["frame"] for r in meta["rows"] if r["state"] == "OK"}
    keys = [k for k in sorted(z.files)
            if k.startswith("b") and k != "bw" and int(k[1:]) in ok]
    return [z[k].astype(np.float64) for k in keys]


def _hann2(h, w):
    return np.outer(np.hanning(h), np.hanning(w))


def bandpow(g):
    g = g - g.mean()
    h, w = g.shape
    F = np.fft.rfft2(g * _hann2(h, w))
    p = F.real ** 2 + F.imag ** 2
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.rfftfreq(w)[None, :]
    rad = np.sqrt(fy ** 2 + fx ** 2)
    return np.array([float(p[(rad >= EDGES[i]) & (rad < EDGES[i + 1])].mean())
                     for i in range(len(EDGES) - 1)])


def s_over_y(rm):
    """S/y from the mean-vs-twin ratio. Clipped at 0: negative means the
    estimate sits below the noise floor, which is 'no signal'."""
    return np.maximum((2.0 * rm - 1.0) / np.maximum(1.0 - rm, 1e-12), 0.0)


def estimate(signal, sigma_map, n, rng):
    """One realisation of the estimator on a KNOWN signal field."""
    y_noise = rng.normal(0.0, 1.0, (n,) + signal.shape).mean(axis=0) * sigma_map
    real_mean = signal + rng.normal(0.0, 1.0, (n,) + signal.shape).mean(axis=0) * sigma_map
    twin_mean = real_mean + y_noise
    return s_over_y(bandpow(real_mean) / np.maximum(bandpow(twin_mean), 1e-30))


def commission(sigma_map, n, rng):
    h, w = sigma_map.shape
    ok, bad = [], []

    # NULL: no scene signal at all -> S/y must be ~0 in every band.
    z = estimate(np.zeros((h, w)), sigma_map, n, rng)
    (ok if z.max() < 0.6 else bad).append(
        "NULL: pure-noise input estimates S/y max %.3f across all bands "
        "(must be ~0)" % z.max())

    # POTENCY: plant a sinusoid at 0.22 cyc/px, which lies in band index 3
    # (0.20-0.25). It must be detected THERE and not elsewhere.
    yy, xx = np.mgrid[0:h, 0:w]
    amp = float(np.median(sigma_map)) * 4.0
    planted = amp * np.sin(2.0 * np.pi * 0.22 * xx)
    p = estimate(planted, sigma_map, n, rng)
    j = EDGES.index(0.20)
    hit = p[j]
    others = np.concatenate([p[:j], p[j + 1:]])
    (ok if hit > 5.0 else bad).append(
        "POTENCY: planted 0.22 cyc/px sinusoid recovered at band 0.20-0.25 "
        "with S/y = %.1f (must be large)" % hit)
    (ok if hit > 5.0 * max(others.max(), 1e-9) else bad).append(
        "LOCALISED: the planted tone reads %.1f at its own band against a "
        "max of %.1f elsewhere (must be well separated)"
        % (hit, others.max()))
    return ok, bad


def main():
    sys.path.insert(0, r"C:\dev\blog\death-of-software\projects\strehl"
                       r"\experiments\V-NEVERWORSE")
    import vn_pyr as VP
    subj = sys.argv[1] if len(sys.argv) > 1 else "112MSDCF"
    os.makedirs(OUT, exist_ok=True)
    frames = np.array(load(subj))
    n = len(frames)
    var0, read2, gph = VP.fit_variance(frames[0][:, :, 1])
    sigma_map = np.sqrt(np.maximum(var0, 0.0))
    rng = np.random.default_rng(20260828)

    print("subject %s, N=%d, read2=%.2f photon_gain=%.5f\n"
          % (subj, n, read2, gph))
    print("commissioning the S/y estimator (both directions):")
    ok, bad = commission(sigma_map, n, rng)
    for l in ok:
        print("  ok      " + l)
    for l in bad:
        print("  FAILED  " + l)
    if bad:
        print("REFUSED: estimator not commissioned")
        return 2

    base = frames.mean(axis=0)[:, :, 1]
    real_mean = base
    twin_mean = base + rng.normal(0.0, 1.0, (n,) + base.shape).mean(axis=0) * sigma_map
    rm = bandpow(real_mean) / np.maximum(bandpow(twin_mean), 1e-30)
    sy = s_over_y(rm)

    hdr = "  %-24s %s" % ("band lo (cyc/px)",
                          "  ".join("%8.2f" % EDGES[i]
                                    for i in range(len(EDGES) - 1)))
    print("\n" + hdr)
    print("  " + "-" * (len(hdr) - 2))
    print("  %-24s %s" % ("mean/twin ratio rm",
                          "  ".join("%8.3f" % v for v in rm)))
    print("  %-24s %s" % ("TRUE SIGNAL  S/y",
                          "  ".join("%8.2f" % v for v in sy)))
    print("\n  (S/y is true scene power in units of the noise left after "
          "averaging all %d frames.\n   S/y ~ 0 means the band is EMPTY of "
          "scene content, not merely faint.)" % n)

    for lo in (0.20, 0.30):
        j = EDGES.index(lo)
        print("\n  %.2f-%.2f cyc/px : rm=%.3f  ->  S/y = %.2f   %s"
              % (EDGES[j], EDGES[j + 1], rm[j], sy[j],
                 "SIGNAL" if sy[j] > 1.0 else "NO MEASURABLE SCENE CONTENT"))

    json.dump(dict(subject=subj, n=n, edges=EDGES, rm=rm.tolist(),
                   s_over_y=sy.tolist()),
              io.open(os.path.join(OUT, "signal_%s.json" % subj), "w",
                      encoding="utf-8"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
