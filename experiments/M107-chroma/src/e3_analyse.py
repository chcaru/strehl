"""E3 analysis: render the argmax maps, and price what a per-channel election
would actually buy.

Discipline: never interpret a spatial statistic without rendering it as a map.
Three separate scalar summaries in this project were overturned tonight by the
rendered map, so the maps come first and the medians second.
"""
import sys, os, json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(__file__))
from common import OUT


def load(stack, tag):
    return np.load(os.path.join(OUT, "json", f"e3_{stack}_{tag}.npz"))


def figure(stacks):
    n = len(stacks)
    fig, axes = plt.subplots(n, 6, figsize=(21, 3.6 * n))
    if n == 1:
        axes = axes[None, :]
    for i, (stack, tag) in enumerate(stacks):
        z = load(stack, tag)
        conf = z["conf"]
        kR, kG1, kG2, kB = z["kR"], z["kG1"], z["kG2"], z["kB"]
        kG = 0.5 * (kG1 + kG2)
        lo, hi = np.percentile(kG[conf], [2, 98])
        for j, (arr, name) in enumerate([(kR, "k_R"), (kG, "k_G  (mean of G1,G2)"),
                                         (kB, "k_B")]):
            a = np.where(conf, arr, np.nan)
            im = axes[i, j].imshow(a, cmap="viridis", vmin=lo, vmax=hi,
                                   interpolation="nearest")
            axes[i, j].set_title(f"{stack}\n{name} argmax frame index", fontsize=8)
            axes[i, j].set_xticks([]); axes[i, j].set_yticks([])
            axes[i, j].set_xlabel(f"stretch: linear, {lo:.0f}-{hi:.0f} frames "
                                  f"(common scale)\ngrey = not confident", fontsize=6)
            plt.colorbar(im, ax=axes[i, j], fraction=0.03)
        # difference maps, on a symmetric diagnostic stretch
        for j, (arr, name) in enumerate([(kR - kG, "k_R - k_G  (SIGNAL)"),
                                         (kB - kG, "k_B - k_G  (SIGNAL)"),
                                         (kG1 - kG2, "k_G1 - k_G2  (NULL)")]):
            a = np.where(conf, arr, np.nan)
            v = 2.5
            im = axes[i, 3 + j].imshow(a, cmap="coolwarm", vmin=-v, vmax=v,
                                       interpolation="nearest")
            med = float(np.median(arr[conf]))
            axes[i, 3 + j].set_title(f"{name}\nmedian {med:+.4f} frames", fontsize=8)
            axes[i, 3 + j].set_xticks([]); axes[i, 3 + j].set_yticks([])
            axes[i, 3 + j].set_xlabel(
                "DIAGNOSTIC STRETCH: coolwarm, +/-2.5 frames, saturating.\n"
                "The three panels share it, so NULL and SIGNAL are comparable.",
                fontsize=6)
            plt.colorbar(im, ax=axes[i, 3 + j], fraction=0.03)
    fig.suptitle(
        "M107 Instrument B -- per-channel frame-of-best-focus, on RAW CFA planes "
        "gathered through the render's own warp sidecar.\n"
        "The right-hand three panels share one stretch: k_G1-k_G2 is the NULL "
        "(same wavelength, different lattice sites, independent noise) and must "
        "read flat if the other two are to be read as axial chromatic aberration.",
        fontsize=10)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    p = os.path.join(OUT, "fig", "M107-fig2-argmax-maps.png")
    fig.savefig(p, dpi=100)
    print("wrote", p)


def stats(stacks):
    rows = {}
    for stack, tag in stacks:
        z = load(stack, tag)
        conf = z["conf"]
        kR, kG1, kG2, kB = z["kR"], z["kG1"], z["kG2"], z["kB"]
        kG = 0.5 * (kG1 + kG2)
        d = {}
        for name, arr in (("dR", kR - kG), ("dB", kB - kG), ("null", kG1 - kG2)):
            v = arr[conf]
            d[name] = {
                "median": float(np.median(v)),
                "mean": float(np.mean(v)),
                "p25": float(np.percentile(v, 25)),
                "p75": float(np.percentile(v, 75)),
                "sd": float(np.std(v)),
                "se_median": float(1.2533 * np.std(v) / np.sqrt(v.size)),
                "frac_same_sign_as_median": float(
                    np.mean(np.sign(v) == np.sign(np.median(v)))),
            }
        d["n_conf"] = int(conf.sum())
        d["ratio_dR_null"] = abs(d["dR"]["median"]) / max(abs(d["null"]["median"]), 1e-9)
        d["ratio_dB_null"] = abs(d["dB"]["median"]) / max(abs(d["null"]["median"]), 1e-9)
        rows[f"{stack}/{tag}"] = d
        print(f"\n{stack} [{tag}]  {conf.sum()} confident px")
        for name in ("dR", "dB", "null"):
            s = d[name]
            print(f"  {name:5s} median {s['median']:+.4f}  mean {s['mean']:+.4f}  "
                  f"IQR [{s['p25']:+.3f},{s['p75']:+.3f}]  sd {s['sd']:.3f}  "
                  f"SE(med) {s['se_median']:.5f}  same-sign {s['frac_same_sign_as_median']*100:.1f}%")
        print(f"  |dR|/|null| = {d['ratio_dR_null']:.1f}x   "
              f"|dB|/|null| = {d['ratio_dB_null']:.1f}x")
    return rows


if __name__ == "__main__":
    stacks = [("tweezers-cpl", "body"), ("bee-3-cpl", "leg-hairs"),
              ("leaf-2-cpl", "veins")]
    stacks = [s for s in stacks
              if os.path.exists(os.path.join(OUT, "json", f"e3_{s[0]}_{s[1]}.npz"))]
    r = stats(stacks)
    figure(stacks)
    with open(os.path.join(OUT, "json", "e3_stats.json"), "w") as f:
        json.dump(r, f, indent=1)
