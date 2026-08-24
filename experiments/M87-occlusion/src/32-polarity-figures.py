"""M87 step 32 -- deliverable figures for the polarity falsifier.

Produces, into C:\\dev\\strehl-out\\M87-before-after\\:

  12-POLARITY-Pplus-error.png   dark foreground on bright background
  12-POLARITY-Pminus-error.png  bright foreground on dark background
  12-POLARITY-side-by-side.png  the two above, same stretch, one image
  13-POLARITY-curves.png        E(d), measured against ground truth and
                                against the truth-free estimator, both arms

Both error maps use the SAME symmetric stretch about zero (mid grey = no
error), so the reversal of sign is a reversal of tone and can be read directly
rather than taken on trust.
"""
import pathlib
import sys

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import importlib.util as _iu  # noqa: E402

_sp = _iu.spec_from_file_location(
    "p24", pathlib.Path(__file__).resolve().parent / "24-polarity-plant.py")
p24 = _iu.module_from_spec(_sp)
_sp.loader.exec_module(p24)

_sp2 = _iu.spec_from_file_location(
    "p29", pathlib.Path(__file__).resolve().parent / "29-real-polarity-v3.py")
p29 = _iu.module_from_spec(_sp2)
_sp2.loader.exec_module(p29)

DEST = pathlib.Path(r"C:\dev\strehl-out\M87-before-after")
DEST.mkdir(parents=True, exist_ok=True)
OUT = pathlib.Path(__file__).resolve().parents[1] / "out"

STRETCH = 0.09          # +-9% of level, common to both arms
CROP = (30, 354, 96, 320)


def to8(a, lo, hi):
    return (np.clip((a - lo) / (hi - lo), 0, 1) * 255).astype(np.uint8)


def label_strip(w, text, h=22):
    from PIL import ImageDraw
    im = Image.new("L", (w, h), 20)
    ImageDraw.Draw(im).text((6, 5), text, fill=235)
    return np.asarray(im)


def main():
    panels, curves = {}, {}
    for tag, fg, bg in (("Pplus", p24.LO, p24.HI), ("Pminus", p24.HI, p24.LO)):
        frames, alphas, m, f, b, truth = p24.build(fg, bg)
        sel, arg = p24.merge(frames, p24.field_signal_dependent)
        near = m > 0.5
        far = ~ndi.binary_dilation(near, np.ones((3, 3)))
        err = sel.astype(np.float64) - truth.astype(np.float64)
        y0, y1, x0, x1 = CROP
        img = to8(err[y0:y1, x0:x1], -STRETCH * p24.LEVEL, STRETCH * p24.LEVEL)
        img = np.asarray(Image.fromarray(img).resize(
            ((x1 - x0) * 2, (y1 - y0) * 2), Image.NEAREST))
        panels[tag] = img
        Image.fromarray(img).save(DEST / f"12-POLARITY-{tag}-error.png")
        curves[tag] = dict(
            truth=p29.curve(sel, truth, near, far, dmax=120),
            est=p29.curve(sel, frames[p24.KF], near, far, dmax=120))
        print(f"  {tag}: wrote 12-POLARITY-{tag}-error.png", flush=True)

    txt = {"Pplus": "DARK foreground on BRIGHT background  ->  DARK error rim",
           "Pminus": "BRIGHT foreground on DARK background  ->  BRIGHT error rim"}
    cols = []
    for tag in ("Pplus", "Pminus"):
        p = panels[tag]
        cols.append(np.vstack([label_strip(p.shape[1], txt[tag]), p]))
    gap = np.full((cols[0].shape[0], 12), 20, np.uint8)
    Image.fromarray(np.hstack([cols[0], gap, cols[1]])).save(
        DEST / "12-POLARITY-side-by-side.png")
    print("  wrote 12-POLARITY-side-by-side.png", flush=True)

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(7.6, 4.4), dpi=150)
        style = {"Pplus": ("#1f77b4", "dark FG / bright BG"),
                 "Pminus": ("#d62728", "bright FG / dark BG")}
        for tag, (col, lab) in style.items():
            d = np.arange(121)
            ax.plot(d, curves[tag]["truth"]["E"], color=col, lw=2,
                    label=f"{lab} — vs ground truth")
            ax.plot(d, curves[tag]["est"]["E"], color=col, lw=1.2, ls="--",
                    label=f"{lab} — truth-free estimator")
        ax.axhline(0, color="k", lw=0.8)
        ax.set_xlabel("distance outward from the silhouette, d (px)")
        ax.set_ylabel("signed error E(d), fraction of level")
        ax.set_title("M87: the occlusion artifact reverses sign with contrast "
                     "polarity\n(synthetic two-layer scene, known ground truth)")
        ax.legend(fontsize=8, framealpha=0.95)
        ax.grid(alpha=0.25)
        fig.tight_layout()
        fig.savefig(DEST / "13-POLARITY-curves.png")
        print("  wrote 13-POLARITY-curves.png", flush=True)
    except ImportError:
        print("  matplotlib unavailable -- skipped the curve figure",
              flush=True)


if __name__ == "__main__":
    main()
