"""S11 -- the side-by-side.

Panels are pixels, not conclusions. No sharpness number is printed on any panel
unless it was measured on that exact axis, so the only numbers here are the
byte-identity count (measured on exactly these pixels, in this script) and the
frame indices.

Everything is rendered through the sRGB transfer curve for viewing only; the
underlying data is linear camera-native and the measurements were all made on
the linear data.
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(__file__))
import m93lib as L  # noqa: E402

HERE = os.path.dirname(os.path.dirname(__file__))
OUTDIR = os.path.join(HERE, "out")
IMGDIR = r"C:\dev\strehl-out\M93-merge-vs-frame"
CROP = 360
ZOOM = 2


def srgb(x):
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def show(plane, lo, hi):
    v = (plane.astype(np.float64) - lo) / max(hi - lo, 1e-9)
    return (255.0 * srgb(v) + 0.5).astype(np.uint8)


def label(img: Image.Image, lines, xy=(10, 8)):
    d = ImageDraw.Draw(img, "RGBA")
    try:
        f = ImageFont.truetype("consola.ttf", 17)
    except OSError:
        f = ImageFont.load_default()
    x, y = xy
    w = max(int(d.textlength(t, font=f)) for t in lines)
    d.rectangle([x - 6, y - 5, x + w + 8, y + 21 * len(lines) + 2], fill=(0, 0, 0, 170))
    for t in lines:
        d.text((x, y), t, font=f, fill=(255, 255, 90))
        y += 21
    return img


def main() -> int:
    os.makedirs(IMGDIR, exist_ok=True)
    rois = json.load(open(os.path.join(OUTDIR, "s2b_rois.json"), encoding="utf-8"))["chosen"]
    focus = json.load(open(os.path.join(OUTDIR, "s3_focus.json"), encoding="utf-8"))["res"]
    armf = json.load(open(os.path.join(OUTDIR, "s4_armF.json"), encoding="utf-8"))
    nm = "ROI-LOWDRIFT"
    x0, y0 = rois[nm]["x"], rois[nm]["y"]
    pk = focus[nm]["peak_frame"]
    elected = np.load(os.path.join(L.OUT, f"m93_elected_{nm}.npy"))

    # Pick the sub-crop where the peak frame itself won most often, so the
    # panels show the region the question is actually about. An earlier version
    # of this script selected |elected - pk| <= 2 and then compared against
    # frame pk alone, which of course does not match on the neighbours; that
    # mistake is recorded in the report.
    near = elected == pk
    from scipy.ndimage import uniform_filter

    dens = uniform_filter(near.astype(np.float32), size=CROP)
    b = CROP // 2 + 4
    dens[:b, :] = dens[-b:, :] = dens[:, :b] = dens[:, -b:] = -1
    cy, cx = np.unravel_index(int(np.argmax(dens)), dens.shape)
    sx, sy = cx - CROP // 2, cy - CROP // 2
    frac_near = float(near[sy : sy + CROP, sx : sx + CROP].mean())
    frac_pm2 = float((np.abs(elected - pk) <= 2)[sy : sy + CROP, sx : sx + CROP].mean())
    print(f"sub-crop within {nm}: plane ({x0+sx},{y0+sy}) size {CROP}, "
          f"{100*frac_near:.1f}% of it elected frame {pk} exactly "
          f"({100*frac_pm2:.1f}% elected {pk} +/- 2)")

    merged = L.read_tif_green(os.path.join(L.OUT, "armM-gate0-binlin.tif"))
    frame = L.read_tif_green(armf["binlin"][str(pk)]["tif"])
    mm = merged[y0 + sy : y0 + sy + CROP, x0 + sx : x0 + sx + CROP]
    ff = frame[y0 + sy : y0 + sy + CROP, x0 + sx : x0 + sx + CROP]
    sel = near[sy : sy + CROP, sx : sx + CROP]
    identical = int((mm[sel] == ff[sel]).sum())
    ntot = int(sel.sum())
    maxdiff = float(np.abs(mm[sel] - ff[sel]).max())
    print(f"on those {ntot} pixels: {identical} byte-identical, max |diff| {maxdiff:.0f} DN of 65535")

    lo = float(np.percentile(mm, 0.5))
    hi = float(np.percentile(mm, 99.7))
    panels = []
    panels.append((show(mm, lo, hi), [
        "A  MERGED  strehl stack --gate 0, alignment OFF",
        "   299 frames -> one frame averaged per pixel",
    ]))
    panels.append((show(ff, lo, hi), [
        f"B  SINGLE FRAME {pk} ({armf['binlin'][str(pk)]['arw']})",
        "   same binary, same decode, same levels, same writer",
    ]))
    d = np.abs(mm.astype(np.float64) - ff.astype(np.float64))
    dsh = show(d * 40.0, 0, 65535)
    dsh_rgb = np.dstack([dsh] * 3)
    edge = sel ^ np.roll(sel, 1, 0)
    edge |= sel ^ np.roll(sel, 1, 1)
    dsh_rgb[edge] = [255, 40, 40]
    panels.append((dsh_rgb, [
        "C  |A - B|, amplified 40x. RED outline = pixels frame " + str(pk) + " won.",
        f"   inside that outline: {identical}/{ntot} pixels byte-identical,",
        f"   max difference {maxdiff:.0f} DN of 65535",
        "   outside it the merge chose a different frame, so A and B differ.",
    ]))

    # Panel D: the same scene through the demosaic path at full sensor
    # resolution, downscaled back to the same display size. This is the sampling
    # the default binned output does not keep.
    import tifffile

    dm = tifffile.imread(armf["demosaic"][str(pk)]["tif"])[:, :, 1].astype(np.float64)
    dtile = dm[2 * (y0 + sy) : 2 * (y0 + sy) + 2 * CROP, 2 * (x0 + sx) : 2 * (x0 + sx) + 2 * CROP]
    panels.append((show(dtile, lo, hi), [
        f"D  SINGLE FRAME {pk}, --demosaic, full sensor grid",
        "   same pixels of subject, twice the samples per axis",
    ]))

    tiles = []
    for arr, lines in panels[:3]:
        a3 = arr if arr.ndim == 3 else np.dstack([arr] * 3)
        im = Image.fromarray(a3).resize((CROP * ZOOM, CROP * ZOOM), Image.NEAREST)
        tiles.append(label(im, lines))
    dmim = Image.fromarray(np.dstack([panels[3][0]] * 3)).resize(
        (CROP * ZOOM, CROP * ZOOM), Image.NEAREST
    )
    tiles.append(label(dmim, panels[3][1]))

    W = CROP * ZOOM
    sheet = Image.new("RGB", (W * 2 + 12, W * 2 + 12 + 74), (18, 18, 18))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % 2) * (W + 12), (i // 2) * (W + 12)))
    label(
        sheet,
        [
            f"M93  bee-3-cpl, 299 frames, ILCE-7CM2 + FE 100mm F2.8 Macro GM OSS + 2X TC, f/5.6 (wide open), ISO 100",
            f"crop: binned plane ({x0+sx},{y0+sy}) {CROP}x{CROP}, shown at {ZOOM}x nearest-neighbour, sRGB transfer for viewing only",
            "A and B are the same scene through the same code path. C is their difference. D is the same frame, not binned.",
        ],
        xy=(10, W * 2 + 20),
    )
    dst = os.path.join(IMGDIR, "M93-merged-vs-single-frame.png")
    sheet.save(dst)
    print(f"wrote          : {dst}   {sheet.size[0]}x{sheet.size[1]}")

    # A second sheet: the election map, which is what the merge actually decided.
    em = elected.astype(np.float64)
    em[em < 0] = np.nan
    v = np.clip((em - np.nanpercentile(em, 2)) / max(np.nanpercentile(em, 98) - np.nanpercentile(em, 2), 1), 0, 1)
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.cm as cm

    rgb = (cm.turbo(np.nan_to_num(v, nan=0.0))[:, :, :3] * 255).astype(np.uint8)
    im2 = Image.fromarray(rgb).resize((512 * 2, 512 * 2), Image.NEAREST)
    label(im2, [
        f"M93  election map read out of the merged file, {nm} 512x512",
        "colour = which of the 299 frames won that pixel (turbo, 2nd-98th pct)",
        f"read by byte-exact match; 99.94% of pixels matched exactly one frame's value",
    ])
    dst2 = os.path.join(IMGDIR, "M93-election-map.png")
    im2.save(dst2)
    print(f"wrote          : {dst2}")

    with open(os.path.join(OUTDIR, "s11_figure.json"), "w", encoding="utf-8") as f:
        json.dump(dict(crop=[int(x0 + sx), int(y0 + sy), CROP], peak=pk,
                       frac_near=frac_near, identical=identical, ntot=ntot,
                       maxdiff=maxdiff, sheet=dst, election=dst2), f, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
