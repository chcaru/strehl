"""H4, the null: does ANY frame of the bracket carry in-focus detail inside the patch?

This renders single frames of the bracket and measures detail inside hand-picked ROIs.

REGISTRATION. `STREHL_ONLY_FRAME` re-solves alignment against the single frame it was
given, so a single-frame render is placed in ITS OWN coordinates, not on the merge's
reference-frame grid -- the render log says `reference frame 0, 1 placed`. Folding such
frames against an ALIGNED merge compares different pixels. So everything here is rendered
with `STREHL_ALIGN=0`, including the merge it is compared against: one unwarped sensor
frame of reference for the whole experiment. Residual frame-to-frame drift is then the
camera's real drift and is reported, not hidden.

NO RESAMPLING. Any registration applied here is an INTEGER pixel shift. The quantity
being measured is sharpness, and sub-pixel resampling adds blur to it.

It saves the crops as pictures as well as the numbers, because the numbers alone cannot
tell the difference between "no frame is sharp here" and "the metric is not looking at
what I think it is looking at".
"""
import argparse
import json
import pathlib
import subprocess
import time

import numpy as np
import tifffile
from PIL import Image, ImageDraw
from scipy import ndimage

Image.MAX_IMAGE_PIXELS = None
BIN = r"C:\dev\strehl-out\pin-1cacb61\target\release\strehl.exe"
SUBJECT = r"D:\personal\macro\flower-bud-alone-cpl"
OUT = pathlib.Path(r"C:\dev\strehl-out\BUILD-ELECT")
REF = np.array([18735.0, 19249.0, 18686.0], dtype=np.float32)


def tone(a):
    x = np.clip(a.astype(np.float32) / (REF[None, None, :] / 0.92), 0.0, 1.0)
    return (np.clip(x ** (1 / 2.2), 0, 1) * 255).astype(np.uint8)


def luma(rgb):
    return (0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]).astype(np.float32)


def detail(g):
    """Two detail statistics, both divided by the local mean so that a brightness
    change through focus cannot masquerade as a detail change."""
    m = float(np.mean(g)) or 1.0
    bp = float(np.sqrt(np.mean(
        (ndimage.gaussian_filter(g, 2.0) - ndimage.gaussian_filter(g, 8.0)) ** 2)))
    gy, gx = np.gradient(g)
    ten = float(np.sqrt(np.mean(gx ** 2 + gy ** 2)))
    return bp / m, ten / m, m


def render_frame(k, dst):
    env_extra = {"STREHL_ALIGN": "0", "STREHL_ONLY_FRAME": str(k)}
    import os
    env = dict(os.environ)
    env.update(env_extra)
    for stale in ("STREHL_DUMP_ELECTION", "STREHL_DUMP_NEFF"):
        env.pop(stale, None)
    r = subprocess.run([BIN, "stack", SUBJECT, "--out", str(dst), "--demosaic"],
                       env=env, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"frame {k} render failed rc={r.returncode}\n{r.stderr[-2000:]}")
    return r.stderr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rois", required=True,
                    help="name:cy:cx:half,name:cy:cx:half ... on the 4688x7040 grid")
    ap.add_argument("--frames", required=True, help="e.g. 0:205:10 or 0,10,20")
    ap.add_argument("--montage-roi", required=True, help="which ROI to montage")
    ap.add_argument("--montage-half", type=int, default=150)
    ap.add_argument("--tag", required=True)
    args = ap.parse_args()

    rois = []
    for spec in args.rois.split(","):
        n, cy, cx, half = spec.split(":")
        rois.append((n, int(cy), int(cx), int(half)))

    if ":" in args.frames:
        a, b, s = (int(x) for x in args.frames.split(":"))
        frames = list(range(a, b, s))
    else:
        frames = [int(x) for x in args.frames.split(",")]

    tmp = OUT / f"_ladder_{args.tag}.tif"
    rows, strips = [], {n: [] for n, _, _, _ in rois}
    t0 = time.time()
    for k in frames:
        render_frame(k, tmp)
        img = tifffile.imread(str(tmp))
        assert img.dtype == np.uint16
        g_all = luma(img)
        rec = {"frame": k}
        for n, cy, cx, half in rois:
            sl = (slice(cy - half, cy + half), slice(cx - half, cx + half))
            bp, ten, m = detail(g_all[sl])
            rec[n] = {"bp_over_mean": bp, "tenengrad_over_mean": ten, "mean_dn": m}
            if n == args.montage_roi:
                h = args.montage_half
                msl = (slice(cy - h, cy + h), slice(cx - h, cx + h))
                strips[n].append((k, tone(img[msl])))
        rows.append(rec)
        print(f"  frame {k:>3}  " + "  ".join(
            f"{n}: bp={rec[n]['bp_over_mean'] * 100:6.3f}% ten={rec[n]['tenengrad_over_mean'] * 100:6.3f}%"
            for n, _, _, _ in rois) + f"   [{time.time() - t0:.0f}s]")
        del img, g_all
        tmp.unlink(missing_ok=True)

    (OUT / f"ladder-{args.tag}.json").write_text(json.dumps(rows, indent=1))

    # A contact sheet through focus. Label every tile with its frame index, so a tile
    # cannot be attributed to the wrong frame by counting.
    tiles = strips[args.montage_roi]
    cols = 7
    rowsn = (len(tiles) + cols - 1) // cols
    th, tw = tiles[0][1].shape[:2]
    sheet = np.zeros((rowsn * th, cols * tw, 3), np.uint8)
    for i, (k, t) in enumerate(tiles):
        r, c = divmod(i, cols)
        sheet[r * th:(r + 1) * th, c * tw:(c + 1) * tw] = t
    im = Image.fromarray(sheet)
    d = ImageDraw.Draw(im)
    for i, (k, _) in enumerate(tiles):
        r, c = divmod(i, cols)
        d.rectangle([c * tw, r * th, c * tw + 46, r * th + 16], fill=(0, 0, 0))
        d.text((c * tw + 4, r * th + 3), f"f{k}", fill=(255, 255, 0))
    dst = OUT / "pics" / f"ladder-{args.tag}-{args.montage_roi}.png"
    im.save(dst)
    print(f"wrote {dst}")


if __name__ == "__main__":
    main()
