"""Render the band-passed chroma of a master beside its source frames.

`orch_chroma.py` flagged coffee-bubbles at 0.0557 against a source maximum of
0.0481 -- the master carries more band-pass chroma energy at 50-300 px than any
frame that went into it. That reading has two mechanisms behind it and the
statistic cannot separate them:

  DEFECT     the merge introduced colour mottling that no input had
  INNOCENT   the merge is sharper, so real colour edges are crisper, and a
             bubble rim at 50-300 px is exactly the scale being measured

Section 96 is the rule this exists to obey: before trusting a positive reading,
name the most plausible innocent explanation and go measure THAT SPECIFIC CAUSE.
An amplitude ladder cannot do it, because both mechanisms scale with amplitude.
A picture can, because the two look completely different:

  mottling appears as soft low-frequency blobs unrelated to subject structure
  sharpened colour appears as thin rims that trace the subject's own edges

Five instruments were wrong tonight and every one was caught by rendering the
thing and looking at it, never by the statistic. This renders three rows at one
stated gain: the crop as seen, the chroma amplified, and the band-passed chroma
that the number is actually computed from.
"""
import os
import sys
import glob

import numpy as np
import tifffile

from orch_chroma import (WIN, LO_R, HI_R, boxblur, relative_chroma,
                         pick_window, SRC_ROOT, OUT_ROOT)
from orch_contact import png_rgb, draw_text, LABEL_H

CROP = 700          # rendered tile, px (centre of the analysis window)
CHROMA_GAIN = 6.0   # amplification for the "chroma boosted" row
BAND_GAIN = 40.0    # band-pass chroma is tiny; this maps +-0.0125 to full scale


def tone(y, lo, hi):
    """One stated window for every tile. Per section 91, a per-tile window
    biases gain and makes tiles incomparable, which is the whole point here."""
    return np.clip((y - lo) / max(hi - lo, 1e-9), 0, 1)


def tiles_for(rgb, at, label):
    """Three tiles from one window: as-seen, chroma-boosted, band-passed chroma."""
    oy, ox = at
    c0 = oy + WIN // 2 - CROP // 2
    c1 = ox + WIN // 2 - CROP // 2
    crop = rgb[c0:c0 + CROP, c1:c1 + CROP].astype(np.float64)

    y = 0.299 * crop[..., 0] + 0.587 * crop[..., 1] + 0.114 * crop[..., 2]
    lo, hi = np.percentile(y, [1, 99])
    seen = np.stack([tone(crop[..., i], lo, hi) for i in range(3)], axis=-1)

    ymean = np.maximum(y, 1.0)
    boost = np.stack(
        [tone(ymean + CHROMA_GAIN * (crop[..., i] - ymean), lo, hi)
         for i in range(3)], axis=-1)

    a, b, _ = relative_chroma(rgb[oy:oy + WIN, ox:ox + WIN])
    ba = boxblur(a, LO_R) - boxblur(a, HI_R)
    bb = boxblur(b, LO_R) - boxblur(b, HI_R)
    m = WIN // 2 - CROP // 2
    ba, bb = ba[m:m + CROP, m:m + CROP], bb[m:m + CROP, m:m + CROP]
    band = np.stack([np.clip(0.5 + BAND_GAIN * ba, 0, 1),
                     np.full_like(ba, 0.5),
                     np.clip(0.5 + BAND_GAIN * bb, 0, 1)], axis=-1)

    rms = float(np.sqrt(np.mean(ba ** 2) + np.mean(bb ** 2)))
    return [(seen, "%s  as seen" % label),
            (boost, "%s  chroma x%.0f" % (label, CHROMA_GAIN)),
            (band, "%s  band-pass x%.0f  rms %.4f" % (label, BAND_GAIN, rms))]


def main():
    subject = sys.argv[1] if len(sys.argv) > 1 else "coffee-bubbles"
    nsrc = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    import rawpy

    mpath = os.path.join(OUT_ROOT, "SHIP-V2", subject + "--SHIP-V2.tiff")
    if not os.path.exists(mpath):
        cand = [p for p in glob.glob(os.path.join(OUT_ROOT, "SHIP-V2", "*.tiff"))
                if subject in os.path.basename(p)]
        if not cand:
            raise SystemExit("no master for %s" % subject)
        mpath = cand[0]
    master = tifffile.imread(mpath)[..., :3]      # tifffile, never PIL
    mat = pick_window(master, "chroma")
    print("master %s  window %r" % (os.path.basename(mpath), mat))

    cols = [tiles_for(master, mat, "MASTER")]

    arw = sorted(glob.glob(os.path.join(SRC_ROOT, subject, "*.ARW")))
    idx = np.linspace(0, len(arw) - 1, min(nsrc, len(arw))).astype(int)
    sat = None
    for i in idx:
        with rawpy.imread(arw[i]) as r:
            s = r.postprocess(gamma=(1, 1), no_auto_bright=True,
                              use_camera_wb=True, output_bps=16)
        if sat is None:
            # THE SAME WINDOW, forced. The first run of this chose each arm's
            # window independently and landed on (0,1458) for the master and
            # (2616,5828) for the source -- two different parts of the subject.
            # The 0.0557-vs-0.0481 comparison that sent me here was between two
            # different scenes, and it would have been published as a chroma
            # defect. The master is warped and cropped relative to the source,
            # but by under 1% (4688x7032 master against a 7040-wide sensor), so
            # shared coordinates are a good approximation and a stated one.
            sat = (min(mat[0], s.shape[0] - WIN), min(mat[1], s.shape[1] - WIN))
            print("source window %r  FORCED to the master's (see comment)" % (sat,))
        cols.append(tiles_for(s, sat, os.path.basename(arw[i])[:12]))

    nrow, ncol = 3, len(cols)
    tw, th = CROP, CROP + LABEL_H
    canvas = np.zeros((nrow * th, ncol * tw, 3), dtype=np.uint8)
    for cx, col in enumerate(cols):
        for ry, (img, lab) in enumerate(col):
            y0, x0 = ry * th, cx * tw
            canvas[y0:y0 + CROP, x0:x0 + CROP] = (img * 255).astype(np.uint8)
            draw_text(canvas, lab, y0 + CROP + 4, x0 + 4)

    outdir = os.path.join(OUT_ROOT, "ORCH-CONTACT")
    os.makedirs(outdir, exist_ok=True)
    out = os.path.join(outdir, "chroma-pair-%s.png" % subject)
    png_rgb(canvas, out)
    print("wrote %s  %dx%d" % (out, canvas.shape[1], canvas.shape[0]))
    print("\nROW 3 IS THE VERDICT. Mottling is soft blobs unrelated to subject")
    print("structure; sharpened colour is thin rims tracing the subject's edges.")
    print("The rms printed on row 3 is the same quantity orch_chroma.py reports,")
    print("computed here on the rendered crop, so the picture and the number")
    print("cannot disagree without one of them being wrong.")


if __name__ == "__main__":
    main()
