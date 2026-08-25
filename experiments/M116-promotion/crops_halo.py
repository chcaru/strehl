"""M116-promotion — the halo images.

Writes to C:\\dev\\strehl-out\\M116\\images-halo\\:

  <subject>__<arm>__full.png            whole render, downscaled to view
  <subject>__<arm>__halo-edge<n>.png    1:1 (100%) crop, IDENTICAL region
  <subject>__contact-halo-edge<n>.png   off / on / delta-80 side by side
  <subject>__DIFF-edge<n>.png           where the correction acted, amplified

The crop windows are chosen ON THE H0 (correction OFF) RENDER by a criterion
that never reads a treated arm: maximise the number of background pixels lying
in the near yoke band (2 <= d <= 25 px of the silhouette) inside the window,
subject to the window straddling the edge (15%..70% foreground). Choosing by
"where the arms differ most" would have picked the window for maximum effect;
ORCH asked for legibility, and a control-arm criterion is what keeps the choice
of what to look at out of the hands of the thing being judged.

Panels are cut from the --srgb renders because they are for looking at. Every
number in the report comes from the linear renders instead: --srgb applies a
non-diagonal colour matrix and a guided demosaic and its own --help says
"For looking at, NOT for measuring."
"""

import json
import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image, ImageDraw
from scipy import ndimage

import score as S
import score_halo as H

ROOT = Path(r"C:\dev\strehl-out\M116")
HALO = ROOT / "halo"
VIEW = HALO / "view"
OUT = ROOT / "images-halo"
SHA = "4beac73"

ARMS = ["H0", "H1", "H2"]
LABEL = {
    "H0": "H0  halo fix OFF  (SHIPPED DEFAULT)",
    "H1": "H1  STREHL_FIX_HALO=1  delta 40",
    "H2": "H2  STREHL_FIX_HALO=1  delta 80",
}
CROP = 512
CROP_VIEW = 1024
BAR = 46
N_WINDOWS = 2


def to_u8(a: np.ndarray) -> np.ndarray:
    if a.dtype == np.uint16:
        return (a >> 8).astype(np.uint8)
    return a.astype(np.uint8)


def labelled(img: Image.Image, text: str, sub: str, sub2: str = "") -> Image.Image:
    out = Image.new("RGB", (img.width, img.height + BAR), (16, 16, 16))
    out.paste(img, (0, BAR))
    d = ImageDraw.Draw(out)
    d.text((6, 4), text, fill=(255, 255, 255))
    d.text((6, 18), sub, fill=(170, 170, 170))
    if sub2:
        d.text((6, 32), sub2, fill=(150, 150, 150))
    return out


def edge_windows(g0: np.ndarray, fg: np.ndarray, n: int):
    """Windows straddling the silhouette, richest in near-yoke background."""
    d = ndimage.distance_transform_edt(~fg)
    near = (~fg) & (d >= 2.0) & (d <= 25.0)
    integ = ndimage.uniform_filter(near.astype(np.float64), size=CROP, mode="constant", cval=0.0)
    fgf = ndimage.uniform_filter(fg.astype(np.float64), size=CROP, mode="constant", cval=0.0)
    h, w = g0.shape
    half = CROP // 2
    # valid[i, j] is the mean over rows [i, i+CROP) -- i, j IS the top-left.
    vnear = integ[half:h - half, half:w - half].copy()
    vfg = fgf[half:h - half, half:w - half]
    vnear[(vfg < 0.15) | (vfg > 0.70)] = -1.0
    picks = []
    scratch = vnear.copy()
    for _ in range(n):
        idx = int(np.argmax(scratch))
        y, x = np.unravel_index(idx, scratch.shape)
        if scratch[y, x] <= 0:
            break
        picks.append((int(y), int(x), float(vnear[y, x]), float(vfg[y, x])))
        y0, y1 = max(0, y - CROP), min(scratch.shape[0], y + CROP)
        x0, x1 = max(0, x - CROP), min(scratch.shape[1], x + CROP)
        scratch[y0:y1, x0:x1] = -1.0   # no overlapping second window
    return picks


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    sc = json.loads((HALO / "scores-halo.json").read_text())
    index = {}

    for s, rec in sc["subjects"].items():
        print(f"==== {s} ====")
        g0 = S.green(HALO / "measure" / f"{s}__H0.tif")
        fg, _ = H.foreground_mask(g0)
        wins = edge_windows(g0, fg, N_WINDOWS)
        if not wins:
            print("  no window straddles an edge; skipping")
            continue
        index[s] = [{"plane_yx": [y, x], "near_frac": nf, "fg_frac": ff}
                    for (y, x, nf, ff) in wins]

        imgs = {}
        for arm in ARMS:
            tif = VIEW / f"{s}__{arm}.tif"
            if not tif.exists():
                print(f"  {tif.name} missing")
                continue
            imgs[arm] = Image.fromarray(to_u8(tifffile.imread(tif)))
            full = imgs[arm].copy()
            full.thumbnail((1400, 1400))
            full.save(OUT / f"{s}__{arm}__full.png")
        if "H0" not in imgs or "H1" not in imgs:
            print("  need H0 and H1 views; skipping")
            continue

        for n, (py, px, nf, ff) in enumerate(wins, start=1):
            x, y = 2 * px, 2 * py
            panels = []
            arrs = {}
            for arm in ARMS:
                if arm not in imgs:
                    continue
                img = imgs[arm]
                xx = max(0, min(x, img.width - CROP_VIEW))
                yy = max(0, min(y, img.height - CROP_VIEW))
                crop = img.crop((xx, yy, xx + CROP_VIEW, yy + CROP_VIEW))
                crop.save(OUT / f"{s}__{arm}__halo-edge{n}.png")
                arrs[arm] = np.asarray(crop).astype(np.int16)
                a = rec["arms"].get(arm, {})
                dh = a.get("dHALO_pct")
                dq = a.get("dQ_fine")
                sub = ("halo index H = "
                       f"{a.get('halo', {}).get('H', float('nan')):+.5f}")
                if dh is not None:
                    sub += f"   dHALO {dh:+.2f}%"
                sub2 = f"dQ(fine) {dq:+.5f}" if dq is not None else "reference arm"
                panels.append(labelled(crop, f"{LABEL[arm]}   [{SHA}]", sub, sub2))

            # amplified difference: where did the correction actually act?
            if "H0" in arrs and "H1" in arrs:
                dif = np.abs(arrs["H1"] - arrs["H0"]).sum(axis=2)
                amp = np.clip(dif.astype(np.float64) * 8.0, 0, 255).astype(np.uint8)
                dimg = Image.fromarray(np.dstack([amp, amp, amp]))
                dimg.save(OUT / f"{s}__DIFF-edge{n}.png")
                panels.append(labelled(
                    dimg, "|H1 - H0| x8   (where the fix acted)",
                    f"{100.0 * float((dif > 0).mean()):.2f}% of this crop changed",
                    "white = changed, black = untouched"))

            cols = len(panels)
            w = sum(p.width for p in panels) + 8 * (cols + 1)
            hh = max(p.height for p in panels) + 44
            sheet = Image.new("RGB", (w, hh), (28, 28, 28))
            xo = 8
            for p in panels:
                sheet.paste(p, (xo, 36))
                xo += p.width + 8
            d = ImageDraw.Draw(sheet)
            d.text((8, 6),
                   f"M116 HALO  {s}  1:1 crop at plane (y={py}, x={px})  "
                   f"commit {SHA}  gate 4  limit 100  --  window chosen on H0 "
                   f"(correction OFF) by near-yoke coverage, never on a treated arm",
                   fill=(255, 255, 255))
            d.text((8, 20),
                   "sRGB renders, for looking at only. Every number in the "
                   "report is measured on the linear renders.",
                   fill=(160, 160, 160))
            sheet.save(OUT / f"{s}__contact-halo-edge{n}.png")
            print(f"  wrote {s}__contact-halo-edge{n}.png  ({cols} panels)")

    (OUT / "crop-index.json").write_text(json.dumps(index, indent=2))
    print(f"\nimages in {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
