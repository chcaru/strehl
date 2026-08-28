# -*- coding: utf-8 -*-
"""V-DILUTE: is 0.30-0.35 cyc/px REALLY noise on 112MSDCF, or is a single
frame just too insensitive to see it?

`vd_band.py` compared ONE real frame against ONE twin frame and found the
0.30-0.35 band at the noise floor (ratio 1.02). That test can be too
conservative: weak scene content buried under single-frame noise would read as
noise even though averaging could recover it. Since V-NEVERWORSE's headline
numbers are scored in that band, the distinction matters and must not be
asserted on the insensitive test alone.

This raises sensitivity by sqrt(N): compare the mean of all N real frames
against the mean of N independent twin frames. Both arms receive exactly the
same 1/sqrt(N) noise reduction, so the comparison stays fair while the noise
floor drops by ~8.9x at N=79.

CAVEAT CARRIED IN THE OUTPUT: the real mean also contains DEFOCUSED frames, so
it understates the scene's recoverable fine content. The real answer is
therefore bracketed, not point-estimated: the single-frame test is a lower
bound on sensitivity, and the mean test is blurred by defocus. Both are
reported and the verdict is only taken where they agree.
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


def main():
    sys.path.insert(0, r"C:\dev\blog\death-of-software\projects\strehl"
                       r"\experiments\V-NEVERWORSE")
    import vn_pyr as VP
    subj = sys.argv[1] if len(sys.argv) > 1 else "112MSDCF"
    os.makedirs(OUT, exist_ok=True)
    frames = np.array(load(subj))
    n = len(frames)
    var0, read2, gph = VP.fit_variance(frames[0][:, :, 1])
    sd = np.sqrt(np.maximum(var0, 0.0))
    rng = np.random.default_rng(20260828)
    base = frames.mean(axis=0)[:, :, 1]

    real_mean = frames[:, :, :, 1].mean(axis=0)
    twin_mean = base + rng.normal(0.0, 1.0, (n,) + base.shape).mean(axis=0) * sd

    p_rm, p_tm = bandpow(real_mean), bandpow(twin_mean)
    p_r1 = bandpow(frames[n // 2][:, :, 1])
    p_t1 = bandpow(base + rng.normal(0.0, 1.0, base.shape) * sd)

    hdr = "  %-26s %s" % ("band lo (cyc/px)",
                          "  ".join("%7.2f" % EDGES[i]
                                    for i in range(len(EDGES) - 1)))
    print("subject %s, N=%d\n" % (subj, n))
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))
    r1 = p_r1 / np.maximum(p_t1, 1e-30)
    rm = p_rm / np.maximum(p_tm, 1e-30)
    print("  %-26s %s" % ("single frame  real/twin",
                          "  ".join("%7.2f" % v for v in r1)))
    print("  %-26s %s" % ("N-frame mean  real/twin",
                          "  ".join("%7.2f" % v for v in rm)))
    print("  %-26s %s" % ("sensitivity gain",
                          "  ".join("%7.2f" % v for v in (rm / np.maximum(r1, 1e-30)))))
    print("\n  per-frame SNR at each band (real/twin - 1, floored at 0):")
    snr = np.maximum(r1 - 1.0, 0.0)
    print("  %-26s %s" % ("", "  ".join("%7.2f" % v for v in snr)))

    i35 = EDGES.index(0.30)
    print("\n  AT 0.30-0.35 (V-NEVERWORSE's scoring band):")
    print("    single frame real/twin = %.3f   -> per-frame SNR %.3f"
          % (r1[i35], snr[i35]))
    print("    N=%d mean   real/twin = %.3f" % (n, rm[i35]))
    i25 = EDGES.index(0.20)
    print("  AT 0.20-0.25 (qualified SIGNAL on this subject):")
    print("    single frame real/twin = %.3f   -> per-frame SNR %.3f"
          % (r1[i25], snr[i25]))
    print("    N=%d mean   real/twin = %.3f" % (n, rm[i25]))

    agree = (r1[i35] < 2.0) and (rm[i35] < 2.0)
    print("\n  VERDICT: %s" % (
        "both tests agree 0.30-0.35 is at/near the noise floor on this "
        "subject -- a sharpness statistic there is scoring grain"
        if agree else
        "the tests DISAGREE; the mean test finds content the single-frame "
        "test missed, so 0.30-0.35 is NOT safely called noise"))
    json.dump(dict(subject=subj, n=n, edges=EDGES, single=r1.tolist(),
                   deep=rm.tolist(), agree=bool(agree)),
              io.open(os.path.join(OUT, "band2_%s.json" % subj), "w",
                      encoding="utf-8"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
