"""M60 step 6 — render every hand-drawn cell so the placement can be checked by eye.

Each cell is drawn on the through-focus MEAN image (the scene under the average
PSF), with the band / FG-interior / BG-interior partition overlaid in colour.
This is the partition the measurement uses, so seeing it is seeing the labels.
"""

import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m60lib as L  # noqa: E402
from cells import CELLS  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.abspath(os.path.join(HERE, "..", "fig"))
DATA = os.path.abspath(os.path.join(HERE, "..", "data"))

BAND_Q = 0.80      # band = top 20% of |grad Ibar| within the cell
FAR_Q = 0.40       # interior = bottom 40%


def partition(Ibar):
    """Split a cell into boundary band, dark interior (FG) and pale interior (BG).

    The split is made on the THROUGH-FOCUS MEAN image only: an intensity
    criterion, applied identically to occlusion and control cells. It never sees
    the focus volume's shape, argmax or peak count.
    """
    from scipy.ndimage import uniform_filter
    gm = L.sobel_mag(Ibar)
    gm = uniform_filter(gm, 5, mode="reflect")
    band = gm >= np.quantile(gm, BAND_Q)
    far = gm <= np.quantile(gm, FAR_Q)
    med = np.median(Ibar)
    return band, far & (Ibar < med), far & (Ibar > med)


def mean_image(stack, crop, step=1):
    fs = L.frames(stack)[::step]
    acc = None
    for f in fs:
        g = L.load_green(f, crop)
        acc = g.astype(np.float64) if acc is None else acc + g
    return (acc / len(fs)).astype(np.float32)


if __name__ == "__main__":
    from PIL import Image
    rows = []
    for stack, name, cls, y0, y1, x0, x1 in CELLS:
        Ibar = mean_image(stack, (y0, y1, x0, x1), step=4)
        band, fg, bg = partition(Ibar)
        hi = float(np.percentile(Ibar, 99.5))
        v = np.clip(Ibar / max(hi, 1e-6), 0, 1) ** (1 / 2.2)
        rgb = np.stack([v, v, v], -1)
        rgb[band] = rgb[band] * 0.45 + np.array([0.55, 0.0, 0.0])
        rgb[fg] = rgb[fg] * 0.65 + np.array([0.0, 0.0, 0.35])
        rgb[bg] = rgb[bg] * 0.65 + np.array([0.0, 0.35, 0.0])
        out = os.path.join(FIG, "06-cell-%s-%s.png" % (cls, name))
        Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8)).save(out)
        rows.append((stack, name, cls, Ibar.size, int(band.sum()), int(fg.sum()), int(bg.sum()),
                     float(np.median(Ibar)), float(np.std(Ibar))))
        print("%-16s %-18s %-8s px=%-8d band=%-7d fg=%-7d bg=%-7d  median %7.1f DN  sd %7.1f"
              % rows[-1][:3] + "" if False else
              "%-16s %-18s %-8s px=%-8d band=%-7d fg=%-7d bg=%-7d  median %7.1f DN  sd %7.1f" % rows[-1])
    with open(os.path.join(DATA, "06-cells.csv"), "w", encoding="utf-8") as fh:
        fh.write("stack,cell,class,px,band_px,fg_px,bg_px,median_dn,sd_dn\n")
        for r in rows:
            fh.write("%s,%s,%s,%d,%d,%d,%d,%.2f,%.2f\n" % r)
