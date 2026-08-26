#!/usr/bin/env python3
"""1:1 crops of BOTH arms, side by side, with the numbers that describe them.

A verdict without a crop is not a verdict.  Two agents on this project have
independently reported the same failure in their own words -- "I did not look at
it as a picture" -- and in both cases the numbers were defensible and the
conclusion was wrong.  So every row of the triage table gets a picture here, and
the picture and the number are printed together and cannot be separated later.

Rules this obeys:

  * NO RESAMPLING of either crop.  Both arms are already on arm A's grid by the
    time they are lifted (compare.py does that with the pipeline's own kernel),
    so the two crops are pixel-registered and can be flicked between.  Scaling
    either one here would be the viewer inventing the sharpness under review.

  * Both crops go through the SAME display transform: a single shared linear
    scale, chosen from arm A, then one gamma.  Per-crop autolevel would make the
    softer arm look better and is exactly how a viewer lies.  The scale is
    printed.

  * The crops are LINEAR-sRGB renders, so a display gamma is applied for viewing
    ONLY.  Every number stamped on them was measured before that gamma, in DN.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tri  # noqa: E402
import compare as C  # noqa: E402

Image.MAX_IMAGE_PIXELS = None


def font(sz: int):
    for p in (r"C:\Windows\Fonts\consola.ttf", r"C:\Windows\Fonts\arial.ttf"):
        try:
            return ImageFont.truetype(p, sz)
        except OSError:
            continue
    return ImageFont.load_default()


def show(rgb: np.ndarray, scale: float) -> Image.Image:
    """One shared linear scale, then one gamma.  Applied identically to both."""
    v = np.clip(rgb.astype(np.float32) * scale, 0.0, 1.0)
    return Image.fromarray((np.power(v, 1 / 2.2) * 255.0 + 0.5).astype(np.uint8))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("subject")
    ap.add_argument("--n", type=int, default=512)
    ap.add_argument("--tag", default="",
                    help="render a tagged compare run (e.g. a regional or "
                         "control run) instead of the corpus sweep")
    args = ap.parse_args()
    sub = args.subject
    n = args.n

    with open(os.path.join(tri.OUT, "compare", sub + args.tag + ".json"),
              encoding="utf-8") as fh:
        cmp_ = json.load(fh)
    ka = cmp_["coverage_k_merge"]
    rgb_a = tri.load16(os.path.join(tri.LIN, sub + ".tiff"))
    ya = tri.luma(rgb_a)

    rows = []
    for label, s in cmp_["sites"].items():
        kf = s["best_frame"]
        tif = os.path.join(C.FRAMEDIR, f"{sub}.f{kf}.tiff")
        if not os.path.exists(tif):
            tif, _ = C.render_frame(sub, kf)
        meta_b = tri.read_log(tif[:-5] + ".log", require=("coverage_k",))
        kb = meta_b["coverage_k"]
        sc = ka / kb
        cy, cx = s["y"], s["x"]

        crop_a = rgb_a[cy:cy + n, cx:cx + n]
        rgb_b = tri.load16(tif)
        wb = np.stack([
            tri.catmull_rom_scale(rgb_b[..., ch], sc,
                                  (s["y"] + s["dy"], s["x"] + s["dx"], n, n))
            for ch in range(3)], axis=-1)
        rows.append((label, s, crop_a, wb))
        del rgb_b

    # One shared display scale for the WHOLE sheet, from arm A, so no crop and
    # no arm is flattered relative to any other.
    hi = max(float(np.percentile(a.astype(np.float32), 99.5)) for _, _, a, _ in rows)
    scale = 1.0 / max(hi, 1.0)

    pad, lab, hdr = 10, 56, 64  # lab grew for the second stamped metric line
    W = 2 * n + 3 * pad
    H = hdr + len(rows) * (n + lab + pad) + pad
    sheet = Image.new("RGB", (W, H), (16, 16, 18))
    d = ImageDraw.Draw(sheet)
    f13, f15, f18 = font(13), font(15), font(18)
    d.text((pad, 10), f"{sub}   MERGE  vs  BEST SOURCE FRAME   1:1, no resampling",
           font=f18, fill=(240, 240, 245))
    d.text((pad, 34),
           f"camera-linear sRGB (no transfer curve) | both arms on the merge grid "
           f"k={ka:.4f} | display: x{scale:.5g} then gamma 2.2, shared",
           font=f13, fill=(150, 150, 160))

    for i, (label, s, ca, cb) in enumerate(rows):
        y = hdr + i * (n + lab + pad)
        hb = s["high"]
        eg = s["edge"]
        d.text((pad, y + 2),
               f"{label}  @({s['x']},{s['y']})  block{tuple(s['block'])}  "
               f"frame {s['best_frame']}  ncc={s['ncc']:.3f}",
               font=f15, fill=(255, 210, 60))
        # PRIMARY metric first, and in a colour that says which way it went.
        good = (eg["ratio"] or 0) >= 0.95
        d.text((pad, y + 21),
               f"edge slope  merge {eg['merge_dnpx']:.0f} DN/px   source "
               f"{eg['frame_dnpx']:.0f}   source corrected "
               f"{eg['frame_corr_dnpx']:.0f}   gather x{eg['gather_cost']:.3f}"
               f"   merge/source = {eg['ratio']}"
               f"   blur-equiv {eg['blur_equiv_px']:.2f} px",
               font=f13, fill=(120, 255, 160) if good else (255, 130, 110))
        # The superseded metric is kept visible so the sheet shows WHY it was
        # superseded: it reads the merge's lower noise as lost detail.
        d.text((pad, y + 37),
               f"pixel noise  merge {eg['noise_merge_dn']:.1f} DN   source "
               f"{eg['noise_frame_dn']:.1f} DN  ({eg['noise_ratio']}x)"
               f"      [superseded high-band metric would say "
               f"{hb['ratio_corr']}]",
               font=f13, fill=(150, 152, 168))
        sheet.paste(show(ca, scale), (pad, y + lab))
        sheet.paste(show(cb, scale), (2 * pad + n, y + lab))
        d.text((pad + 4, y + lab + 4),
               f"MERGE  mean {s['level']['merge_mean_dn']:.0f} DN", font=f13,
               fill=(255, 255, 255))
        d.text((2 * pad + n + 4, y + lab + 4),
               f"SOURCE f{s['best_frame']}  mean {s['level']['frame_mean_dn']:.0f} DN"
               f"  (delta {s['level']['delta_dn']:+.0f})",
               font=f13, fill=(255, 255, 255))

    os.makedirs(os.path.join(tri.OUT, "crops"), exist_ok=True)
    op = os.path.join(tri.OUT, "crops", sub + args.tag + ".jpg")
    sheet.save(op, quality=95, subsampling=0)
    print(f"{sub}: -> {op}  ({sheet.size[0]}x{sheet.size[1]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
