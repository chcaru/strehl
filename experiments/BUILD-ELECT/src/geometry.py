"""Whole-frame look at the winner field, and the geometry tests for H1 and H3.

Two jobs.

1. A FULL-FRAME picture. This project has twice shipped a defect that was obvious in
   three seconds of looking at the whole frame and invisible in 100% crops, so the whole
   frame is looked at first.

2. Geometry of the winner field, against nulls:
   * H3 (a tile grid leaking through) -- row and column mean power spectra of the winner
     field. A tile grid is an EXACT pitch, so it shows as a spike at an integer period
     and its harmonics. The null is the same spectrum from a smooth synthetic field.
   * H1 (box-window plateaus at the 27x27 focus window) -- orientation histogram of the
     seam tangents against a uniform null (a box filter makes AXIS-ALIGNED straight
     edges, so excess mass near 0 and 90 degrees is its signature), and the size
     distribution of constant-index plateaus against the 27 px window diameter.
"""
import argparse
import pathlib

import numpy as np
import tifffile
from PIL import Image, ImageDraw
from matplotlib import colormaps
from scipy import ndimage

Image.MAX_IMAGE_PIXELS = None
OUT = pathlib.Path(r"C:\dev\strehl-out\BUILD-ELECT")
REF = np.array([18735.0, 19249.0, 18686.0], dtype=np.float32)
WINDOW_DIAM = 27.0      # focus.rs WINDOW_RADIUS = 13 -> 27x27 plane px
REG_DIAM = 17.0         # merge.rs REGULARISER_RADIUS = 8 -> 17x17 plane px


def tone(a):
    x = np.clip(a.astype(np.float32) / (REF[None, None, :] / 0.92), 0.0, 1.0)
    return (np.clip(x ** (1 / 2.2), 0, 1) * 255).astype(np.uint8)


def colorise(a, cmap="turbo"):
    a = a.astype(np.float32)
    lo, hi = float(a.min()), float(a.max())
    x = np.clip((a - lo) / max(hi - lo, 1e-6), 0, 1)
    return (colormaps[cmap](x)[..., :3] * 255).astype(np.uint8), lo, hi


def label(img, text):
    im = Image.fromarray(np.ascontiguousarray(img))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, len(text) * 7 + 10, 20], fill=(0, 0, 0))
    d.text((5, 5), text, fill=(255, 255, 255))
    return np.asarray(im)


def full_frame(merge_p, elect_p, neff_p, tag):
    merge = tifffile.imread(str(merge_p))
    elect = tifffile.imread(str(elect_p))
    neff = tifffile.imread(str(neff_p))
    assert merge.dtype == elect.dtype == neff.dtype == np.uint16
    k = 4
    m = tone(merge[::2 * k, ::2 * k])
    e, lo, hi = colorise(elect[::k, ::k])
    n, nlo, nhi = colorise(neff[::k, ::k], cmap="viridis")
    h = min(m.shape[0], e.shape[0], n.shape[0])
    w = min(m.shape[1], e.shape[1], n.shape[1])
    sheet = np.concatenate([label(m[:h, :w], f"{tag} merge"),
                            label(e[:h, :w], f"winner idx {lo:.0f}-{hi:.0f}"),
                            label(n[:h, :w], f"n_eff {nlo:.0f}-{nhi:.0f}")], axis=1)
    dst = OUT / "pics" / f"FULL-{tag}.png"
    Image.fromarray(sheet).save(dst)
    print(f"wrote {dst}  ({sheet.shape[1]}x{sheet.shape[0]})")
    return elect


def spectra(e, tag):
    """H3: an exact tile pitch would be a spike at an integer period."""
    f = e.astype(np.float32)
    f = f - ndimage.uniform_filter(f, 65)          # remove the smooth depth ramp
    f *= np.hanning(f.shape[0])[:, None] * np.hanning(f.shape[1])[None, :]
    prow = np.abs(np.fft.rfft(f, axis=1)) ** 2
    pcol = np.abs(np.fft.rfft(f, axis=0)) ** 2
    prow = prow.mean(axis=0)
    pcol = pcol.mean(axis=1)
    print(f"\n[{tag}] H3 -- tile-pitch search (period in PLANE px, "
          f"peaks scored as z above a local median baseline)")
    for name, p, n in (("rows(x)", prow, f.shape[1]), ("cols(y)", pcol, f.shape[0])):
        k = np.arange(len(p))
        with np.errstate(divide="ignore"):
            per = np.where(k > 0, n / np.maximum(k, 1), np.inf)
        band = (per >= 4) & (per <= 512)
        pb, perb = p[band], per[band]
        base = ndimage.median_filter(pb, 51)
        mad = ndimage.median_filter(np.abs(pb - base), 51) + 1e-30
        z = (pb - base) / (1.4826 * mad)
        order = np.argsort(z)[::-1][:6]
        top = ", ".join(f"{perb[i]:.1f}px z={z[i]:.1f}" for i in sorted(order, key=lambda i: -z[i]))
        print(f"  {name}: top periods  {top}")
    return prow, pcol


def orientation_and_plateaus(e, tag):
    """H1: box windows make AXIS-ALIGNED straight edges at the window scale."""
    ei = e.astype(np.int32)
    gy, gx = np.gradient(ei.astype(np.float32))
    mag = np.hypot(gx, gy)
    thr = np.percentile(mag, 99.0)
    sel = mag > thr
    ang = (np.degrees(np.arctan2(gy[sel], gx[sel])) % 180.0)
    # distance to the nearer axis (0 or 90); uniform null gives mean 22.5 deg
    d_axis = np.minimum(np.minimum(ang, np.abs(ang - 90.0)), np.abs(ang - 180.0))
    frac10 = float(np.mean(d_axis < 10.0))
    print(f"\n[{tag}] H1 -- seam orientation, n={sel.sum()} strongest-1% gradient pixels")
    print(f"  within 10 deg of an axis : {100 * frac10:.2f}%   "
          f"(uniform null = {100 * 20.0 / 90.0:.2f}%)")
    print(f"  mean distance to an axis : {d_axis.mean():.2f} deg  (uniform null = 22.50)")

    lab, nl = ndimage.label(np.abs(np.gradient(ei.astype(np.float32))[0]) < 1e-6)
    sizes = np.bincount(lab.ravel())[1:]
    sizes = sizes[sizes >= 9]
    if len(sizes):
        d = 2.0 * np.sqrt(sizes / np.pi)
        print(f"  constant-index plateaus  : n={len(sizes)}  "
              f"median equiv diameter {np.median(d):.1f} px, p90 {np.percentile(d, 90):.1f} px")
        print(f"  reference scales         : focus window {WINDOW_DIAM:.0f} px, "
              f"regulariser {REG_DIAM:.0f} px")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--merge", required=True)
    ap.add_argument("--elect", required=True)
    ap.add_argument("--neff", required=True)
    ap.add_argument("--tag", required=True)
    args = ap.parse_args()
    e = full_frame(args.merge, args.elect, args.neff, args.tag)

    # whole plane, then the two crops, then a smooth synthetic null
    spectra(e, f"{args.tag}/whole-plane")
    orientation_and_plateaus(e, f"{args.tag}/whole-plane")
    for name, (cy, cx) in (("upper-lobe", (1056, 1232)), ("lower-lobe", (1584, 1936))):
        sub = e[cy - 175:cy + 175, cx - 175:cx + 175]
        spectra(sub, f"{args.tag}/{name}")
        orientation_and_plateaus(sub, f"{args.tag}/{name}")

    rng = np.random.default_rng(7)
    smooth = ndimage.gaussian_filter(rng.normal(size=(350, 350)), 20)
    smooth = (60 * (smooth - smooth.min()) / (smooth.ptp() if hasattr(smooth, "ptp")
                                              else (smooth.max() - smooth.min()))).astype(np.uint16)
    spectra(smooth, "NULL/smooth-synthetic")
    orientation_and_plateaus(smooth, "NULL/smooth-synthetic")


if __name__ == "__main__":
    main()
