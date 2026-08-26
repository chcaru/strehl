"""How much of the SUBJECT is carved into hard-edged cells, and is anything blended?

Three things, all from artifacts already on disk -- no render.

1. n_eff inside the subject against n_eff over the backdrop. n_eff is the number of
   frames pass two averages. Where it is ~1 the merge is SELECTING, and a selected
   output is a mosaic of whole frames with nothing blended across the joins.

2. A picture of the subject with every winner-index seam painted, so the cell structure
   can be seen rather than inferred from a statistic.

3. Whether seams are visible in the image: the merged luma's gradient magnitude ON seam
   pixels against OFF seam pixels, with the mandatory translated-mask control (a
   coincidence statistic without its null is not a number). The translation is chosen to
   destroy per-pixel correspondence while preserving the mask's spatial statistics.
"""
import argparse
import pathlib

import numpy as np
import tifffile
from PIL import Image, ImageDraw
from scipy import ndimage

Image.MAX_IMAGE_PIXELS = None
OUT = pathlib.Path(r"C:\dev\strehl-out\BUILD-ELECT")
REF = np.array([18735.0, 19249.0, 18686.0], dtype=np.float32)


def tone(a):
    x = np.clip(a.astype(np.float32) / (REF[None, None, :] / 0.92), 0.0, 1.0)
    return (np.clip(x ** (1 / 2.2), 0, 1) * 255).astype(np.uint8)


def seam_mask(e, jump):
    d = np.zeros(e.shape, bool)
    ei = e.astype(np.int32)
    d[:-1, :] |= np.abs(np.diff(ei, axis=0)) > jump
    d[:, :-1] |= np.abs(np.diff(ei, axis=1)) > jump
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--merge", required=True)
    ap.add_argument("--elect", required=True)
    ap.add_argument("--neff", required=True)
    ap.add_argument("--tag", required=True)
    args = ap.parse_args()

    merge = tifffile.imread(args.merge)
    elect = tifffile.imread(args.elect)
    neff = tifffile.imread(args.neff)
    assert merge.dtype == elect.dtype == neff.dtype == np.uint16
    lum = (0.2126 * merge[..., 0] + 0.7152 * merge[..., 1]
           + 0.0722 * merge[..., 2]).astype(np.float32)

    # Subject mask, by the same rule ORCH-rim/rimprofile.py used: the backdrop is bright.
    p5, p95 = np.percentile(lum, 5), np.percentile(lum, 95)
    thr = p5 + 0.5 * (p95 - p5)
    subj = lum < thr
    subj = ndimage.binary_closing(subj, np.ones((15, 15)))
    subj = ndimage.binary_opening(subj, np.ones((15, 15)))
    lab, nl = ndimage.label(subj)
    subj = lab == (1 + int(np.argmax(ndimage.sum(subj, lab, range(1, nl + 1)))))
    psubj = subj[::2, ::2]
    print(f"threshold {thr:.0f} DN; subject = {100 * subj.mean():.2f}% of frame")

    # 1. n_eff, subject vs backdrop
    n = neff.astype(np.float32)
    dist_out = ndimage.distance_transform_edt(~psubj)
    far = dist_out > 300
    print("\n--- n_eff: is anything being averaged where the defect lives? ---")
    for name, m in (("SUBJECT", psubj), ("backdrop >300px out", far)):
        v = n[m]
        print(f"  {name:<22} n={v.size:>9}  median {np.median(v):6.1f}  "
              f"mean {v.mean():7.1f}  p10 {np.percentile(v, 10):5.1f}  "
              f"p90 {np.percentile(v, 90):6.1f}  frac(n_eff<=3) {100 * np.mean(v <= 3):5.1f}%")

    # 2 + 3. Seams, painted and scored.
    print("\n--- winner-index seams inside the subject ---")
    print(f"  {'jump':>5}{'seam px':>10}{'% of subject':>14}"
          f"{'|grad lum| ON':>15}{'OFF':>10}{'ratio':>8}{'translated ctl':>16}{'ctl ratio':>11}")
    gy, gx = np.gradient(lum)
    gmag = np.hypot(gx, gy)
    gp = gmag[::2, ::2]  # plane grid, to match the seam mask
    rng = np.random.default_rng(11)
    for jump in (1, 4, 16, 64):
        s = seam_mask(elect, jump) & psubj
        off = psubj & ~ndimage.binary_dilation(s, np.ones((5, 5)))
        on_v, off_v = gp[s], gp[off]
        # translated-mask control: same mask, shifted far enough to break correspondence
        ctl = np.roll(seam_mask(elect, jump), (137, 211), axis=(0, 1)) & psubj
        ctl_v = gp[ctl]
        if on_v.size < 100 or ctl_v.size < 100:
            print(f"  {jump:>5}{s.sum():>10}  (too few pixels to score)")
            continue
        print(f"  {jump:>5}{s.sum():>10}{100 * s.sum() / psubj.sum():>13.2f}%"
              f"{np.median(on_v):>15.1f}{np.median(off_v):>10.1f}"
              f"{np.median(on_v) / max(np.median(off_v), 1e-6):>8.2f}"
              f"{np.median(ctl_v):>16.1f}"
              f"{np.median(ctl_v) / max(np.median(off_v), 1e-6):>11.2f}")

    # The picture: the whole subject, seams painted.
    ys, xs = np.where(subj)
    y0, y1 = int(ys.min()), int(ys.max()) + 1
    x0, x1 = int(xs.min()), int(xs.max()) + 1
    k = 3
    img = tone(merge[y0:y1, x0:x1])[::k, ::k]
    for jump, colour in ((64, (255, 0, 0)), (16, (255, 180, 0))):
        s = np.repeat(np.repeat(seam_mask(elect, jump), 2, 0), 2, 1)[y0:y1, x0:x1][::k, ::k]
        s &= np.repeat(np.repeat(psubj, 2, 0), 2, 1)[y0:y1, x0:x1][::k, ::k]
        img[s] = colour
    im = Image.fromarray(img)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 430, 20], fill=(0, 0, 0))
    d.text((5, 5), f"{args.tag}: winner seams in subject  red |d|>64  amber |d|>16",
           fill=(255, 255, 255))
    dst = OUT / "pics" / f"SEAMS-{args.tag}.png"
    im.save(dst)
    print(f"\nwrote {dst}")


if __name__ == "__main__":
    main()
