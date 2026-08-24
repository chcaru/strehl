"""Figure 8 -- render what A1 measured, instead of trusting its scalars.

Three separate confident measurements in this project were overturned tonight by
rendering them, and in every case the wrong answer arrived with more apparent
precision than the right one. A1 produced an R^2 of 0.1309 on leaf-2-cpl, the one
number in that table that could be read as "depth-dependence is real". So it gets
looked at rather than quoted.

Panels, per stack: the k_R - k_G map itself, and the binned relationship against
depth with the G1-G2 null drawn on the SAME axes. Plotting the null beside the
signal is the whole point -- a trend that the null also shows is not a trend.
"""
import sys, os, glob
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(__file__))
from common import OUT

FIG = os.path.join(OUT, "fig")
os.makedirs(FIG, exist_ok=True)


def binned(x, y, nb=24):
    lo, hi = np.percentile(x, [1, 99])
    edges = np.linspace(lo, hi, nb + 1)
    idx = np.digitize(x, edges) - 1
    xs, ys, es = [], [], []
    for b in range(nb):
        m = idx == b
        if m.sum() < 50:
            continue
        xs.append(0.5 * (edges[b] + edges[b + 1]))
        ys.append(np.median(y[m]))
        es.append(np.std(y[m]) / np.sqrt(m.sum()))
    return np.array(xs), np.array(ys), np.array(es)


def main():
    files = sorted(glob.glob(os.path.join(OUT, "json", "e3_*.npz")))
    fig, axes = plt.subplots(2, len(files), figsize=(5.2 * len(files), 9.0))

    for j, f in enumerate(files):
        tag = os.path.basename(f)[3:-4]
        z = np.load(f)
        kG = 0.5 * (z["kG1"] + z["kG2"])
        dR = z["kR"] - kG
        null = z["kG1"] - z["kG2"]
        m = z["conf"].astype(bool) & np.isfinite(dR) & np.isfinite(null)

        # --- top: the map, diagnostic stretch, stated on the panel ---
        ax = axes[0, j]
        disp = np.where(m, dR, np.nan)
        lo, hi = np.nanpercentile(disp, [2, 98])
        im = ax.imshow(disp, cmap="coolwarm", vmin=lo, vmax=hi)
        ax.set_title(f"{tag}\n$k_R - k_G$  (frames)", fontsize=10)
        ax.set_xticks([]); ax.set_yticks([])
        ax.text(0.02, 0.02,
                f"DIAGNOSTIC STRETCH: 2-98 pct = [{lo:.2f}, {hi:.2f}] frames\n"
                f"grey = below confidence gate  ({100*m.mean():.0f}% kept)",
                transform=ax.transAxes, fontsize=7, va="bottom",
                bbox=dict(fc="white", alpha=0.8, ec="none"))
        plt.colorbar(im, ax=ax, fraction=0.046)

        # --- bottom: signal vs depth, with the null on the same axes ---
        ax = axes[1, j]
        x1, y1, e1 = binned(kG[m], dR[m])
        x2, y2, e2 = binned(kG[m], null[m])
        ax.errorbar(x1, y1, yerr=e1, fmt="o-", ms=4, lw=1.4, color="crimson",
                    label="$k_R - k_G$  (signal)")
        ax.errorbar(x2, y2, yerr=e2, fmt="s-", ms=4, lw=1.4, color="0.35",
                    label="$k_{G1} - k_{G2}$  (NULL)")
        ax.axhline(0.0, color="k", lw=0.8, ls=":")
        ax.axhline(np.median(dR[m]), color="crimson", lw=0.8, ls="--",
                   label=f"constant-offset model ({np.median(dR[m]):+.2f})")
        ax.set_xlabel("elected green frame index $k_G$  (depth proxy)")
        ax.set_ylabel("frame offset")
        ax.set_title("depth dependence, binned medians", fontsize=10)
        ax.legend(fontsize=7, loc="best")
        ax.grid(alpha=0.25)
        ax.text(0.02, 0.02,
                "error bars = SEM of the bin\nno stretch; raw frame units",
                transform=ax.transAxes, fontsize=7, va="bottom",
                bbox=dict(fc="white", alpha=0.8, ec="none"))

    fig.suptitle(
        "M107b fig8 -- A1: is the axial offset depth-dependent?  "
        "The null is plotted on the same axes because a trend the null also "
        "shows is not a trend.",
        fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    p = os.path.join(FIG, "fig8-a1-depth.png")
    fig.savefig(p, dpi=120)
    print("wrote", p)


if __name__ == "__main__":
    main()
