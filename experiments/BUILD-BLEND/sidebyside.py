"""Side-by-side full frames and 1:1 crops, estimator vs pyramid.

The project's standing rule is that if the pictures and the number disagree, the
pictures are right, and that a merge is judged on FULL FRAMES rather than on
crops it chose. So this writes both, from the same TIFF pair, with the arms
labelled and rendered through an identical transform.

Two disciplines are load-bearing here and both are cheap to get wrong:

  * Never open a 16-bit RGB TIFF with PIL -- it silently hands back 8-bit.
    tifffile, and assert uint16.
  * Both arms MUST go through the same tone transform. Scaling each arm to its
    own percentiles would hide exactly the level differences the comparison is
    about, so the mapping is computed on the CONTROL and applied to both.

The 1:1 crop is taken at a fixed location supplied by the caller rather than
searched for, because a crop chosen by scoring the output is a crop chosen to
flatter it.
"""

import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image, ImageDraw


def load(p):
    im = tifffile.imread(str(p))
    assert im.dtype == np.uint16, f"{p}: expected uint16, got {im.dtype}"
    assert im.ndim == 3 and im.shape[2] == 3, f"{p}: expected HxWx3, got {im.shape}"
    return im


def tone(im, lo, hi):
    """Identical transform for both arms: linear -> percentile stretch -> sRGB."""
    x = (im.astype(np.float32) - lo) / max(hi - lo, 1.0)
    np.clip(x, 0.0, 1.0, out=x)
    x = np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)
    return (x * 255.0 + 0.5).astype(np.uint8)


def label(img, text):
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 8 * len(text) + 12, 26], fill=(0, 0, 0))
    d.text((6, 7), text, fill=(255, 255, 0))
    return img


def main():
    subject, ctrl_p, treat_p, outdir = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    cx = int(sys.argv[5]) if len(sys.argv) > 5 else None
    cy = int(sys.argv[6]) if len(sys.argv) > 6 else None
    Path(outdir).mkdir(parents=True, exist_ok=True)

    a, b = load(ctrl_p), load(treat_p)
    assert a.shape == b.shape, (a.shape, b.shape)

    # Mapping fixed on the control, applied to both arms.
    lo = float(np.percentile(a[::8, ::8], 0.5))
    hi = float(np.percentile(a[::8, ::8], 99.5))
    print(f"{subject}: tone from control, {lo:.0f}..{hi:.0f} DN")

    ta, tb = tone(a, lo, hi), tone(b, lo, hi)
    h, w, _ = ta.shape

    # --- full frame, side by side --------------------------------------------
    sc = 1400 / w
    fw, fh = int(w * sc), int(h * sc)
    ia = label(Image.fromarray(ta).resize((fw, fh), Image.LANCZOS), "estimator (shipped default)")
    ib = label(Image.fromarray(tb).resize((fw, fh), Image.LANCZOS), "pyramid (--merge pyramid)")
    sxs = Image.new("RGB", (fw * 2 + 12, fh), (24, 24, 24))
    sxs.paste(ia, (0, 0))
    sxs.paste(ib, (fw + 12, 0))
    p1 = Path(outdir) / f"sxs-{subject}.jpg"
    sxs.save(p1, quality=92)
    print(f"  {p1}")

    # --- 1:1 crop ------------------------------------------------------------
    if cx is not None and cy is not None:
        s = 700
        x0, y0 = max(0, cx - s // 2), max(0, cy - s // 2)
        x1, y1 = min(w, x0 + s), min(h, y0 + s)
        ca = label(Image.fromarray(ta[y0:y1, x0:x1]), "estimator")
        cb = label(Image.fromarray(tb[y0:y1, x0:x1]), "pyramid")
        cw, ch = ca.size
        crop = Image.new("RGB", (cw * 2 + 12, ch), (24, 24, 24))
        crop.paste(ca, (0, 0))
        crop.paste(cb, (cw + 12, 0))
        p2 = Path(outdir) / f"crop-{subject}.jpg"
        crop.save(p2, quality=95)
        print(f"  {p2}  (1:1 at {cx},{cy})")


if __name__ == "__main__":
    main()
