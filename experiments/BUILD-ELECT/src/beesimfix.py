"""Test my own remedy on the bee, per pixel, and try to break it.

Phase 1 on flower-bud proposed high-passing the luma before the gradient, so that
a smooth veil ramp can no longer be scored as focus. That was measured on a subject
where a real texture peak existed and the veil outscored it. The bee ladder says
two of its defect ROIs have NO texture peak at all: the through-focus texture curve
is flat to within 1.13-1.25x of its own floor across 299 frames.

A flat curve is the case that breaks the remedy. argmax over a flat curve is not
"more accurate", it is a coin flip, and a coin flip per pixel is speckle. So the
question this asks is not "does the remedy help" but "where does it hurt", and the
comparison is run per pixel over whole crops rather than on ROI medians, because
speckle is invisible in a median.

Three rules, same data:
  A  argmax(full)            what the binary ships
  B  argmax(high)            the Phase 1 remedy
  C  argmax(high) + abstain  B, but pixels whose peak does not clear its own floor
                             by ABSTAIN_TAU do not get to vote; they take the median
                             of the confident pixels around them instead

Judged on two things that pull against each other: how far the elected frame sits
from the local surface, and how much seam energy the winner field carries. A rule
that wins on one and loses badly on the other has not fixed anything.
"""
import argparse
import json
import pathlib

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter, median_filter, uniform_filter

OUT = pathlib.Path(r"C:\dev\strehl-out\BUILD-ELECT\bee")
PICS = OUT / "pics"
REF = np.array([19093.0, 20163.0, 21361.0])

WINDOW_RADIUS = 13
LOW_SIGMA = 8.0
ABSTAIN_TAU = 1.30      # peak must clear its own floor by this to be allowed to vote
REG_R = 8               # merge.rs REGULARISER_RADIUS, for the regularisation mimic
FILL_R = 12             # plane px; radius of the neighbour prior for abstained pixels


def sobel_mag(a):
    p = np.pad(a, 1, mode="edge")
    gx = (p[:-2, 2:] + 2.0 * p[1:-1, 2:] + p[2:, 2:]
          - p[:-2, :-2] - 2.0 * p[1:-1, :-2] - p[2:, :-2]) * 0.125
    gy = (p[2:, :-2] + 2.0 * p[2:, 1:-1] + p[2:, 2:]
          - p[:-2, :-2] - 2.0 * p[:-2, 1:-1] - p[:-2, 2:]) * 0.125
    return np.hypot(gx, gy)


def focus_of(a):
    return uniform_filter(sobel_mag(a), size=2 * WINDOW_RADIUS + 1, mode="nearest")


def tone(rgb):
    return np.clip(rgb.astype(np.float64) / (REF / 0.92), 0, 1) ** (1 / 2.2)


def seam_energy(w):
    """Mean absolute frame-index step across neighbours: how visible the patchwork is."""
    return float(np.mean(np.abs(np.diff(w, axis=0))) + np.mean(np.abs(np.diff(w, axis=1)))) / 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="crops")
    args = ap.parse_args()
    PICS.mkdir(parents=True, exist_ok=True)

    src = OUT / f"ladder-{args.tag}"
    files = sorted(src.glob("f*.npz"))
    frames = np.array([int(f.stem[1:]) for f in files])
    names = list(np.load(files[0]).keys())
    elected = json.loads((OUT / "bee-rois.json").read_text())

    rows = []
    fig, axes = plt.subplots(len(names), 5, figsize=(21, 4.1 * len(names)))
    for r, n in enumerate(names):
        full, high, mid = [], [], None
        for f in files:
            rgb = np.load(f)[n].astype(np.float64)
            g = rgb[:, :, 1]
            L = 0.25 * (g[0::2, 0::2] + g[0::2, 1::2] + g[1::2, 0::2] + g[1::2, 1::2])
            full.append(focus_of(L))
            high.append(focus_of(L - gaussian_filter(L, LOW_SIGMA, mode="nearest")))
            if int(f.stem[1:]) == frames[np.argmin(np.abs(frames - elected[n]["elected"]))]:
                mid = rgb
        full = np.stack(full); high = np.stack(high)

        wA = frames[np.argmax(full, 0)].astype(np.float64)
        wB = frames[np.argmax(high, 0)].astype(np.float64)
        prom = high.max(0) / np.maximum(high.min(0), 1e-9)
        conf = prom >= ABSTAIN_TAU
        # Abstained pixels take the mean of the confident pixels around them. Where
        # nothing nearby is confident there is no prior either, and the pixel keeps
        # its own value rather than having one invented for it.
        conf_f = conf.astype(np.float64)
        cnt = uniform_filter(conf_f, 2 * FILL_R + 1, mode="nearest")
        tot = uniform_filter(np.where(conf, wB, 0.0), 2 * FILL_R + 1, mode="nearest")
        fillv = np.where(cnt > 1e-6, tot / np.maximum(cnt, 1e-9), wB)
        wC = np.where(conf, wB, fillv)

        row = {"roi": n, "elected": elected[n]["elected"],
               "abstain_frac": float(1 - conf.mean()),
               "seam_A": seam_energy(wA), "seam_B": seam_energy(wB),
               "seam_C": seam_energy(wC),
               "spread_A": float(np.percentile(wA, 95) - np.percentile(wA, 5)),
               "spread_B": float(np.percentile(wB, 95) - np.percentile(wB, 5)),
               "spread_C": float(np.percentile(wC, 95) - np.percentile(wC, 5))}

        # Threat to this comparison: A, B and C above are all raw per-pixel argmax,
        # while the shipped field is regularised (merge_cmd.rs 1167-1215,
        # REGULARISER_RADIUS = 8). If regularisation would clean up B's speckle, the
        # claim that B is harmful is overstated. Mimic it -- a median filter at the
        # shipped radius, applied identically to all three -- and re-measure.
        for k, w in (("A", wA), ("B", wB), ("C", wC)):
            wr = median_filter(w, size=2 * REG_R + 1, mode="nearest")
            row[f"regseam_{k}"] = seam_energy(wr)
            row[f"regspread_{k}"] = float(np.percentile(wr, 95) - np.percentile(wr, 5))
        rows.append(row)

        axes[r, 0].imshow(tone(mid[125:375, 125:375]), interpolation="nearest")
        axes[r, 0].set_title(f"{n}: merge-elected frame f{row['elected']:.0f}",
                             fontsize=10)
        for c, (w, t) in enumerate(((wA, "A argmax(full) = shipped"),
                                    (wB, "B argmax(high) = Phase 1 remedy"),
                                    (wC, "C remedy + abstain")), start=1):
            im = axes[r, c].imshow(w, cmap="turbo", vmin=frames[0], vmax=frames[-1],
                                   interpolation="nearest")
            axes[r, c].set_title(f"{t}\nseam {seam_energy(w):.1f}", fontsize=10)
            plt.colorbar(im, ax=axes[r, c], fraction=.045)
        axes[r, 4].imshow(conf, cmap="gray", interpolation="nearest")
        axes[r, 4].set_title(f"confident pixels\nabstain {row['abstain_frac']:.0%}",
                             fontsize=10)
        for c in range(5):
            axes[r, c].set_xticks([]); axes[r, c].set_yticks([])
        print(f"  {n:<11} abstain {row['abstain_frac']:>6.1%}  seam A {row['seam_A']:>6.2f}"
              f"  B {row['seam_B']:>6.2f}  C {row['seam_C']:>6.2f}   "
              f"spread A {row['spread_A']:>5.0f} B {row['spread_B']:>5.0f} "
              f"C {row['spread_C']:>5.0f}", flush=True)

    print(f"\n{'-' * 78}\nregularisation mimic (median filter r={REG_R}, applied to all "
          f"three rules alike)\n{'-' * 78}")
    print(f"  {'roi':<11} {'seam A*':>8} {'B*':>8} {'C*':>8}   {'spread A*':>9} "
          f"{'B*':>6} {'C*':>6}")
    for row in rows:
        print(f"  {row['roi']:<11} {row['regseam_A']:>8.2f} {row['regseam_B']:>8.2f} "
              f"{row['regseam_C']:>8.2f}   {row['regspread_A']:>9.0f} "
              f"{row['regspread_B']:>6.0f} {row['regspread_C']:>6.0f}")
    survives = [r["roi"] for r in rows if r["regseam_B"] > r["regseam_A"] * 1.5]
    print(f"  -> B still worse than A after regularisation at: {survives}")
    if not survives:
        print("     Regularisation absorbs the damage; the 'remedy is harmful' claim\n"
              "     does not survive its own falsification test.")

    fig.suptitle("bee-1-cpl: the Phase 1 remedy tested per pixel. Rule B is a coin "
                 "flip wherever the texture curve is flat.", fontsize=14)
    fig.tight_layout()
    p = PICS / "BEE-simfix.png"
    fig.savefig(p, dpi=100); plt.close(fig)

    print(f"\n{'=' * 78}")
    bad = [r for r in rows if r["seam_B"] > r["seam_A"] * 1.5]
    print(f"ROIs where the remedy alone makes the winner field MORE broken: "
          f"{[r['roi'] for r in bad]}")
    fixed = [r for r in rows if r["seam_C"] < r["seam_B"]]
    print(f"ROIs where abstention repairs that: {[r['roi'] for r in fixed]}")
    (OUT / "bee-simfix.json").write_text(json.dumps(rows, indent=1))
    print(f"wrote {p}")


if __name__ == "__main__":
    main()
