"""1:1 crop montages across BUILD-SHARP arms, at frozen coordinates.

Coordinates come from the project's frozen ROI plan (`C:\\dev\\strehl-out\\roi-plan.json`),
which is on the BINNED grid, multiplied by 2 for the full-resolution renders.
Rule 11: the plan is READ, never re-planned.

Every panel of a montage gets the SAME display gain, computed once from the
first arm, so a brightness difference cannot masquerade as a contrast
difference.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import bslib as B

PLAN = Path(r"C:\dev\strehl-out\roi-plan.json")


def load_plan(subject: str) -> dict:
    with open(PLAN) as f:
        return json.load(f)[subject]


def label(img: Image.Image, text: str) -> Image.Image:
    out = Image.new("RGB", (img.width, img.height + 18), (0, 0, 0))
    out.paste(img, (0, 18))
    ImageDraw.Draw(out).text((3, 3), text, fill=(255, 255, 255))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", required=True)
    ap.add_argument("--arms", nargs="+", required=True)
    ap.add_argument("--rois", nargs="+", default=["detail0", "detail1", "detail2"])
    ap.add_argument("--size", type=int, default=384)
    ap.add_argument("--zoom", type=int, default=1)
    ap.add_argument("--out", required=True)
    ap.add_argument("--mono", action="store_true", help="green channel only")
    a = ap.parse_args()

    plan = load_plan(a.subject)
    imgs = {}
    for arm in a.arms:
        p = B.arm(a.subject, arm)
        if not p.exists():
            raise SystemExit(f"missing arm render: {p}")
        imgs[arm] = B.read_linear(p)

    ref = imgs[a.arms[0]]
    full_res = ref.shape[0] > 3000
    scale = 2 if full_res else 1
    gain = B.display_gain(ref)

    outdir = Path(a.out)
    outdir.mkdir(parents=True, exist_ok=True)

    for roi in a.rois:
        kind = roi.rstrip("0123456789")
        i = int(roi[len(kind):])
        # The plan stores [x, y] -- see `plan_subject` in scripts/crop_set.py,
        # which writes `[[int(x), int(y)] for x, y in v]`.
        x, y = plan["rois"][kind][i]
        y, x = y * scale, x * scale
        s = a.size
        panels = []
        for arm in a.arms:
            patch = imgs[arm][y : y + s, x : x + s]
            if patch.shape[0] != s or patch.shape[1] != s:
                raise SystemExit(f"{arm} {roi}: crop out of bounds {patch.shape}")
            if a.mono:
                g = patch[..., 1]
                px = B.to_png8(np.dstack([g, g, g]), gain, colour=False)
            else:
                px = B.to_png8(patch, gain, colour=True)
            im = Image.fromarray(px)
            if a.zoom > 1:
                im = im.resize((s * a.zoom, s * a.zoom), Image.NEAREST)
            panels.append(label(im, f"{arm}"))

        w = sum(p.width for p in panels) + 4 * (len(panels) - 1)
        h = max(p.height for p in panels)
        sheet = Image.new("RGB", (w, h), (32, 32, 32))
        xo = 0
        for p in panels:
            sheet.paste(p, (xo, 0))
            xo += p.width + 4
        dst = outdir / f"{a.subject}-{roi}.png"
        sheet.save(dst)
        print(f"{dst}  ({y},{x}) {s}px x{a.zoom}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
