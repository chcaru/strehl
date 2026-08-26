"""Pick ladder ROIs on bee-1-cpl, and draw them so they can be checked by eye.

A detector built on guessed thresholds returns nothing and looks exactly like a
negative result, so this does not get to choose silently. It proposes ROIs from
the align-off winner field, prints their statistics, and draws a labelled picture.
The picture is the gate: if a box is not sitting where its label says, the box is
wrong and the ladder built on it would be measuring the wrong thing.

Four ROIs, chosen to make the H4 test decidable:
  blob        inside a high-index island on the foreleg  -- the defect
  leg-good    the surrounding leg surface                -- the neighbour it seams against
  fringe      the flat patch in the hair fringe          -- the second defect instance
  bee-sharp   well-resolved thorax                       -- the control that must be correct

All coordinates are on the ALIGN-OFF render, because the ladder frames are rendered
with STREHL_ALIGN=0 and single-frame renders otherwise sit in their own coordinates.
"""
import json
import pathlib

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import tifffile
from scipy import ndimage

OUT = pathlib.Path(r"C:\dev\strehl-out\BUILD-ELECT\bee")
PICS = OUT / "pics"
REF = np.array([19093.0, 20163.0, 21361.0])
HALF = 250          # ladder crop half-size, output px

# Search windows on the 4688 x 7032 output grid, (y0, y1, x0, x1), and the rule.
# Thresholds are absolute and come from what was visible in BEE2-*: the flat blobs
# elect f245+ while the leg they seam against elects f180. Percentile rules were
# tried first and picked mixed ground (n_eff 51), which the picture caught.
SEARCH = {
    "blob":      ((1744, 2504, 645, 1405), ("hi", 245)),
    "leg-good":  ((1744, 2504, 645, 1405), ("band", 175, 195)),
    "fringe":    ((1202, 1962, 1011, 1771), ("hi", 288)),
    "fringe-ok": ((1202, 1962, 1011, 1771), ("band", 60, 140)),
    "bee-sharp": ((1800, 2800, 3200, 4400), ("band", 40, 48)),
}


def tone(rgb):
    return np.clip(rgb.astype(np.float64) / (REF / 0.92), 0, 1) ** (1 / 2.2)


def pick(e, box, rule):
    """Centre of the largest connected region matching the rule, clamped."""
    y0, y1, x0, x1 = box
    sub = e[y0 // 2:y1 // 2, x0 // 2:x1 // 2]
    if rule[0] == "hi":
        m = sub >= rule[1]
    else:
        m = (sub >= rule[1]) & (sub <= rule[2])
    m = ndimage.binary_opening(m, np.ones((9, 9)))
    lab, nl = ndimage.label(m)
    if nl == 0:
        raise SystemExit(f"no region found for {box} {rule}")
    big = 1 + int(np.argmax(ndimage.sum(m, lab, range(1, nl + 1))))
    # argmax of the distance transform, not the centroid: a ring-shaped or
    # crescent region has its centroid in the hole. The mask is zero-padded first
    # because distance_transform_edt treats the array border as interior, which
    # otherwise puts every pick in a corner of the search window.
    d = ndimage.distance_transform_edt(np.pad(lab == big, 1))[1:-1, 1:-1]
    py, px = np.unravel_index(int(np.argmax(d)), d.shape)
    cy, cx = 2 * (py + y0 // 2), 2 * (px + x0 // 2)
    return int(cy), int(cx), float(d.max())


def main():
    PICS.mkdir(parents=True, exist_ok=True)
    e = tifffile.imread(str(OUT / "E-noalign-elect.tif")).astype(np.int32)
    n = tifffile.imread(str(OUT / "E-noalign-neff.tif")).astype(np.int32)
    img = tifffile.imread(str(OUT / "E-noalign-merge.tif"))
    assert img.dtype == np.uint16, img.dtype
    H, W = img.shape[:2]

    rois = {}
    print(f"{'roi':<12} {'cy':>6} {'cx':>6} {'inradius':>9} {'elected':>9} "
          f"{'p5-p95':>12} {'n_eff':>7}")
    for name, (box, rule) in SEARCH.items():
        cy, cx, r = pick(e, box, rule)
        cy = int(np.clip(cy, HALF, H - HALF)); cx = int(np.clip(cx, HALF, W - HALF))
        s = (slice((cy - 60) // 2, (cy + 60) // 2), slice((cx - 60) // 2, (cx + 60) // 2))
        v, nv = e[s], n[s]
        rois[name] = {"cy": cy, "cx": cx,
                      "elected": float(np.median(v)),
                      "p5": float(np.percentile(v, 5)),
                      "p95": float(np.percentile(v, 95)),
                      "n_eff": float(np.median(nv))}
        print(f"{name:<12} {cy:>6} {cx:>6} {r:>9.1f} {np.median(v):>9.0f} "
              f"{np.percentile(v, 5):>5.0f}-{np.percentile(v, 95):<6.0f} "
              f"{np.median(nv):>7.0f}")

    fig, axes = plt.subplots(1, 2, figsize=(21, 7.6))
    small = tone(img[::4, ::4])
    axes[0].imshow(small)
    axes[0].set_title("align-off merge, whole frame", fontsize=12)
    im = axes[1].imshow(e[::2, ::2], cmap="turbo", interpolation="nearest")
    axes[1].set_title("winner index", fontsize=12)
    plt.colorbar(im, ax=axes[1], fraction=.03)
    for ax, sc in ((axes[0], 4), (axes[1], 4)):
        for name, r in rois.items():
            ax.add_patch(mpatches.Rectangle(
                ((r["cx"] - 60) / sc, (r["cy"] - 60) / sc), 120 / sc, 120 / sc,
                fill=False, ec="red", lw=2))
            ax.text(r["cx"] / sc, (r["cy"] - 80) / sc,
                    f"{name} f{r['elected']:.0f}", color="red", fontsize=11,
                    ha="center", weight="bold")
        ax.set_xticks([]); ax.set_yticks([])
    fig.suptitle("bee-1-cpl ladder ROIs -- check every box sits where its label says",
                 fontsize=14)
    fig.tight_layout()
    p = PICS / "BEE-rois.png"
    fig.savefig(p, dpi=100); plt.close(fig)
    (OUT / "bee-rois.json").write_text(json.dumps(rois, indent=1))
    print(f"\nwrote {p}")


if __name__ == "__main__":
    main()
