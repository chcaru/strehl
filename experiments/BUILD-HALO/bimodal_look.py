"""Look at where the bimodality detector fires, against the frozen edge ROIs.

ORCH's question is spatial, not statistical: *does the detector land on the
rim and blob pixels?* A firing rate cannot answer that -- a detector could hit
14% of the blob population and still be firing on the wrong 14%. So this puts
the render, the detector and the fix's own coverage map side by side in the
same window and lets the eye adjudicate, which is this build's standing rule.

Reads only 16-bit TIFFs via tifffile with an explicit dtype assert, because
PIL silently downconverts 16-bit RGB to 8.
"""

import argparse
import os

import numpy as np
import tifffile


def stretch(a, lo=1.0, hi=99.0):
    """Percentile stretch to 8-bit for viewing only. Never used for numbers."""
    p0, p1 = np.percentile(a, [lo, hi])
    if p1 <= p0:
        p1 = p0 + 1e-6
    return np.clip((a - p0) / (p1 - p0), 0, 1)


def heat(v):
    """Black -> red -> yellow -> white, so 'where it fires' reads at a glance."""
    v = np.clip(v, 0, 1)
    r = np.clip(3 * v, 0, 1)
    g = np.clip(3 * v - 1, 0, 1)
    b = np.clip(3 * v - 2, 0, 1)
    return np.dstack([r, g, b])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", required=True, help="STREHL_BIMODAL_DUMP directory")
    ap.add_argument("--render", required=True, help="linear.tif for the same run")
    ap.add_argument("--out", required=True)
    ap.add_argument("--rois", required=True, help="x,y;x,y;...")
    ap.add_argument("--crop", type=int, default=384, help="plan ROI box size")
    ap.add_argument("--zfire", type=float, default=3.02, help="operating threshold")
    args = ap.parse_args()

    rgb = tifffile.imread(args.render)
    assert rgb.dtype == np.uint16, f"render is {rgb.dtype}, refusing to guess"
    z = tifffile.imread(os.path.join(args.dump, "bimodal-second-mode-z.tif"))
    blend = tifffile.imread(os.path.join(args.dump, "edge-aware-blend.tif"))
    assert z.dtype == np.uint16 and blend.dtype == np.uint16
    z = z.astype(np.float32) / 6553.5
    blend = blend.astype(np.float32) / 65535.0

    # The plan states each ROI as a top-left corner plus a box size, and the
    # baseline crops were cut that way. Match it exactly or the comparison is
    # against different windows.
    box = args.crop
    rows = []
    for spec in args.rois.split(";"):
        x, y = (int(t) for t in spec.split(","))
        y0, y1 = y, min(rgb.shape[0], y + box)
        x0, x1 = x, min(rgb.shape[1], x + box)
        img = stretch(rgb[y0:y1, x0:x1].astype(np.float32).mean(axis=2))
        img = np.dstack([img] * 3)
        zz = heat(z[y0:y1, x0:x1] / 5.0)
        # Where it FIRES, over the picture, so the two can be registered by eye.
        fire = z[y0:y1, x0:x1] >= args.zfire
        over = img.copy()
        over[fire] = [1.0, 0.15, 0.0]
        bl = heat(blend[y0:y1, x0:x1])
        gap = np.ones((y1 - y0, 6, 3))
        rows.append(np.hstack([img, gap, zz, gap, over, gap, bl]))

    sep = np.ones((6, rows[0].shape[1], 3))
    out = rows[0]
    for r in rows[1:]:
        out = np.vstack([out, sep, r])
    tifffile.imwrite(args.out, (out * 65535).astype(np.uint16), photometric="rgb")
    print(f"wrote {args.out}  ({out.shape[1]}x{out.shape[0]})")
    print("columns: render | second-mode z (heat) | fires>=%.2f in orange | fix coverage"
          % args.zfire)


if __name__ == "__main__":
    main()
