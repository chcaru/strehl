"""M98 D4 -- the owner-facing gate ladder.

M85's `gate-ladder.png` is the format: same crop per row, same display gain
within a row, one row of fine detail and one of smooth background, with the
measured cost and benefit stated on the panel.  This is that, with alignment ON
and the numbers replaced by ones measured at HEAD.

RULE 5 / M85 section 5: the sRGB+demosaic renders exist ONLY to be looked at.
No number on this panel is measured from them -- every number is carried in
from the linear camera-native measurement path (s4_fullstack.py).  The panel
states which is which.

Usage:  python s5_artefact.py
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m98lib as M98  # noqa: E402

OUTDIR = r"C:\dev\strehl-out\M98"
GATES = [0.0, 0.5, 1.0, 2.0, 4.0]
CELL = 320          # displayed cell, px
CROP = 320          # source crop, px, 1:1 -- no resampling of the evidence

# mean frames averaged per pixel, MEASURED at HEAD with alignment ON by
# `strehl stack D:\personal\macro\bee-3-cpl --gate 0 0.5 1 2 4` -- the ladder
# the merge prints for itself.  Carried in, not recomputed here.
N_EFF = {0.0: 1.000, 0.5: 1.968, 1.0: 4.562, 2.0: 19.182, 4.0: 55.321}


def srgb_path(gate):
    return os.path.join(M98.RENDERS, f"bee-3-cpl-VIEW-g{gate:g}.tif")


def font(sz):
    for n in ("consola.ttf", "arial.ttf", "seguisb.ttf"):
        try:
            return ImageFont.truetype(n, sz)
        except OSError:
            continue
    return ImageFont.load_default()


def load_rgb8(path):
    import tifffile
    a = tifffile.imread(path)
    if a.dtype == np.uint16:
        a = (a.astype(np.float64) / 65535.0)
    else:
        a = a.astype(np.float64) / 255.0
    return a


def main():
    for g in GATES:
        if not os.path.exists(srgb_path(g)):
            print(f"MISSING {srgb_path(g)} -- run render-view.ps1 first")
            return
    stats = json.load(open(os.path.join(M98.OUT, "s4_bee-3-cpl.json")))
    aln = stats["arms"]["ALN"]
    hp = stats["hp_sd"]
    grid = stats["grid"]

    imgs = {g: load_rgb8(srgb_path(g)) for g in GATES}
    H, W, _ = imgs[0.0].shape

    # Rows: the highest-detail ROI and the lowest-detail ROI, chosen by the
    # frozen hp_sd stratifier -- not by eye.
    k_hi = int(np.argmax(hp))
    k_lo = int(np.argmin(hp))
    rows = []
    for k, label in ((k_hi, "FINE DETAIL"), (k_lo, "SMOOTH BACKGROUND")):
        x, y = grid[k]
        # centre the display crop inside the measured 512 ROI
        cx = int(x + M98.ROI // 2)
        cy = int(y + M98.ROI // 2)
        # the measurement plane is binned 2x1 per quad; the sRGB render is full
        # sensor resolution, so the ROI centre scales by W / measured width.
        sx = W / float(stats["w"])
        sy = H / float(stats["h"])
        rows.append((label, k, int(cx * sx), int(cy * sy)))

    pad, top, left = 6, 116, 210
    ann = 118
    wpx = left + len(GATES) * (CELL + pad) + pad
    hpx = top + len(rows) * (CELL + pad + ann) + pad + 52
    canvas = Image.new("RGB", (wpx, hpx), (16, 16, 18))
    d = ImageDraw.Draw(canvas)
    f_h = font(23)
    f_m = font(15)
    f_s = font(13)

    d.text((pad + 4, 10), "strehl --gate  |  bee-3-cpl, 299 frames, "
           "ALIGNMENT ON (HEAD)", font=f_h, fill=(240, 240, 245))
    d.text((pad + 4, 42), "Same crop per row, same display gain within a row. "
           "sRGB+demosaic, for LOOKING AT ONLY -- every number below is "
           "measured on the linear camera-native path.", font=f_s,
           fill=(150, 150, 160))
    d.text((pad + 4, 62), "Left = the merge takes ONE frame per pixel. "
           "Right = the shipped default. The question is what the trip from "
           "left to right costs.", font=f_s, fill=(150, 150, 160))

    for gi, g in enumerate(GATES):
        cxp = left + gi * (CELL + pad)
        lab = f"--gate {g:g}" + ("   [SHIPPED DEFAULT]" if g == 4.0 else
                                 ("   [pure selector]" if g == 0.0 else ""))
        d.text((cxp, top - 44), lab, font=f_m,
               fill=(255, 214, 120) if g == 4.0 else (200, 200, 210))
        d.text((cxp, top - 22), f"{N_EFF[g]:.3f} frames averaged / pixel",
               font=f_s, fill=(150, 150, 160))
    d.text((pad + 4, top - 22), "mean n_eff, whole frame:", font=f_s,
           fill=(150, 150, 160))

    for ri, (label, k, cx, cy) in enumerate(rows):
        y0 = top + ri * (CELL + pad + ann)
        # one display gain for the whole row, from the gate-0 crop
        ref = imgs[0.0][max(cy - CROP // 2, 0):max(cy - CROP // 2, 0) + CROP,
                        max(cx - CROP // 2, 0):max(cx - CROP // 2, 0) + CROP]
        lo = float(np.percentile(ref, 1.0))
        hi = float(np.percentile(ref, 99.5))
        if hi <= lo:
            hi = lo + 1e-3
        d.text((pad + 4, y0 + 6), label, font=f_m, fill=(240, 240, 245))
        d.text((pad + 4, y0 + 28), f"ROI {k}", font=f_s, fill=(150, 150, 160))
        d.text((pad + 4, y0 + 46), f"detail hp_sd {hp[k]:.0f}", font=f_s,
               fill=(150, 150, 160))
        d.text((pad + 4, y0 + 70), f"display gain fixed", font=f_s,
               fill=(110, 110, 120))
        d.text((pad + 4, y0 + 86), f"on the gate-0 crop", font=f_s,
               fill=(110, 110, 120))
        for gi, g in enumerate(GATES):
            a = imgs[g][max(cy - CROP // 2, 0):max(cy - CROP // 2, 0) + CROP,
                        max(cx - CROP // 2, 0):max(cx - CROP // 2, 0) + CROP]
            v = np.clip((a - lo) / (hi - lo), 0, 1)
            tile = Image.fromarray((v * 255).astype(np.uint8))
            if tile.size != (CELL, CELL):
                tile = tile.resize((CELL, CELL), Image.NEAREST)
            cxp = left + gi * (CELL + pad)
            canvas.paste(tile, (cxp, y0))
            if g == 4.0:
                d.rectangle([cxp - 1, y0 - 1, cxp + CELL, y0 + CELL],
                            outline=(255, 214, 120), width=2)

            row = aln["per_gate"][f"{g:g}"][k]
            base = aln["per_gate"]["0"][k]
            ty = y0 + CELL + 6
            npow = row["floor_ratio"]
            nsig = np.sqrt(npow) if npow > 0 else float("nan")
            lines = [
                (f"noise      {nsig:.3f}x", (140, 220, 150)),
                (f"HF amp     {row['clean_ratio']:.4f}x", (215, 215, 225)),
                (f"blur cost  {row['dsig']:+.3f} px", (240, 170, 150)),
            ]
            if g == 0.0:
                lines = [("noise      1.000x  (reference)", (140, 220, 150)),
                         ("HF amp     1.0000x", (215, 215, 225)),
                         ("blur cost  0.000 px", (240, 170, 150))]
            for li, (t, col) in enumerate(lines):
                d.text((cxp + 3, ty + li * 18), t, font=f_s, fill=col)
            _ = base

        d.text((pad + 4, y0 + CELL + 6), "measured, linear path:", font=f_s,
               fill=(150, 150, 160))
        d.text((pad + 4, y0 + CELL + 26), "noise = sigma of the", font=f_s,
               fill=(110, 110, 120))
        d.text((pad + 4, y0 + CELL + 42), "above-cutoff floor", font=f_s,
               fill=(110, 110, 120))
        d.text((pad + 4, y0 + CELL + 62), "blur cost = m57 dsig", font=f_s,
               fill=(110, 110, 120))
        d.text((pad + 4, y0 + CELL + 78), "vs gate 0, +ve = softer", font=f_s,
               fill=(110, 110, 120))

    d.text((pad + 4, hpx - 48),
           "M98. Cost and benefit are both measured on the same renders. "
           "Read the two rows together: the gate buys its noise reduction "
           "everywhere and spends its sharpness only where there is detail.",
           font=f_s, fill=(150, 150, 160))
    d.text((pad + 4, hpx - 30),
           "External check, not from this frame: on flat-on-ruler-cpl -- a "
           "millimetre ruler, tick pitch known a priori -- gate 4 resolves "
           "0.99894 +/- 0.00065 of the gate-0 modulation, an equivalent blur "
           "of +0.033 +/- 0.037 px.",
           font=f_s, fill=(150, 150, 160))
    d.text((pad + 4, hpx - 14),
           "If you want every last cycle on the facets, use --gate 1: it "
           "keeps 0.998x of the fine-detail amplitude for half the noise "
           "benefit. --gate 0 is not the sharp option; it is the noisy one.",
           font=f_s, fill=(200, 200, 210))

    os.makedirs(OUTDIR, exist_ok=True)
    out = os.path.join(OUTDIR, "gate-ladder.png")
    canvas.save(out)
    print(f"wrote {out}  ({wpx} x {hpx})")


if __name__ == "__main__":
    main()
