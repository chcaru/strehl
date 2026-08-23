"""M60 — diagnostic: look at the plant's own through-focus curves.

P1's D=0 null produced z* = 16-18, i.e. the 99th-percentile "second peak" in a
strictly single-depth plant stands 17 predicted-sigma above its dip. Either the
noise denominator is wrong or the plant is not actually unimodal. Look before
believing either.
"""

import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib
P = importlib.import_module("13-plant")
FIG = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fig"))


if __name__ == "__main__":
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rng = np.random.default_rng(4242)
    n, kF, W = 120, 40, 192
    veil = slice(int(W * 0.42), int(W * 0.42) + 24)
    fig, axes = plt.subplots(2, 2, figsize=(13, 8))
    for ax, (D, rate) in zip(axes.ravel(), [(0, 0.5), (60, 0.5), (0, 0.25), (60, 0.25)]):
        F, S, alpha = P.p1_stack(rng, n, kF, kF + D, rate)
        z, k1, k2, prom, den = P.run_detector(F, S)
        v = F[:, :, veil].reshape(n, -1)
        s = S[:, :, veil].reshape(n, -1)
        zz = z[:, veil].ravel()
        order = np.argsort(zz)
        for j in order[-4:]:
            ax.plot(v[:, j], lw=1.0, label="z=%.1f" % zz[j])
        ax.plot(np.median(v, axis=1), "k--", lw=2, label="median")
        ax.plot(np.median(s, axis=1) * 20, "r:", lw=1.5, label="20 x median predicted sd")
        ax.set_title("D=%d rate=%.2f   median den=%.3f  median prom=%.3f"
                     % (D, rate, np.median(den[:, veil]), np.median(prom[:, veil])))
        ax.legend(fontsize=7)
        ax.set_xlabel("frame")
    plt.tight_layout()
    plt.savefig(os.path.join(FIG, "14-plant-curves.png"), dpi=110)

    # is the denominator plausible? compare the MC sd to the frame-to-frame
    # scatter of the curve in a region where the scene is genuinely flat
    F, S, alpha = P.p1_stack(rng, n, kF, kF, 0.5)
    v = F[:, :, veil].reshape(n, -1)
    s = S[:, :, veil].reshape(n, -1)
    d2 = np.diff(v, axis=0)
    print("D=0 plant, veil zone:")
    print("  median predicted sd of f_k              %.4f" % np.median(s))
    print("  median |f_k - f_{k-1}| / sqrt(2)        %.4f"
          % (np.median(np.abs(d2)) / np.sqrt(2) / 0.6745))
    print("  sd of the curve about a 5-frame median  %.4f"
          % np.median(np.std(v - np.median(v, axis=0, keepdims=True), axis=0)))
    print("  median prominence of the 2nd peak       %.4f"
          % np.median(P.run_detector(F, S)[3][:, veil]))
