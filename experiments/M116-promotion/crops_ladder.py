"""M116-promotion -- contact sheets for the DELTA dose ladder.

Two sheets per subject, both at 1:1 (no resampling of image content):

  * `ladder`  -- the same crop across rungs, captioned with the rung, so the
                 dose response is visible rather than asserted.
  * `oriented`-- LB7: a crop chosen for ORIENTED fine structure (hairs, claws,
                 antennae), H0 against the shipped delta 40, published whether
                 or not it shows a cost.

Window selection runs on H0 only, which is not a compared arm, so the crop
cannot be chosen to flatter a treatment.

Views are sRGB at a frozen exposure: for looking at, not for measuring. Every
number in the report comes from the linear renders.

Run: python crops_ladder.py
"""

import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image, ImageDraw
from scipy import ndimage

import score as S
import score_halo as SH
import score_ladder as SL

ROOT = Path(r"C:\dev\strehl-out\M116")
HALO = ROOT / "halo"
OUT = ROOT / "images-ladder"

CROP = 640
BAR = 46

# (view tag, caption) in ladder order. H0 first.
BEE_LADDER = [("H0", "OFF"), ("V1", "delta 1"), ("V40", "delta 40  (SHIPPED)"),
              ("V160", "delta 160")]
FERN_LADDER = [("H0", "OFF"), ("V40", "delta 40  (SHIPPED)")]


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


def pick_window(weight: np.ndarray, shape, n: int = 1):
    """Top-left corners of the CROP-square windows richest in `weight`."""
    integ = ndimage.uniform_filter(weight.astype(np.float64), size=CROP,
                                   mode="constant", cval=0.0)
    h, w = shape
    half = CROP // 2
    v = integ[half:h - half, half:w - half].copy()
    picks, scratch = [], v.copy()
    for _ in range(n):
        idx = int(np.argmax(scratch))
        y, x = np.unravel_index(idx, scratch.shape)
        if scratch[y, x] <= 0:
            break
        picks.append((int(y), int(x), float(v[y, x])))
        y0, y1 = max(0, y - CROP), min(scratch.shape[0], y + CROP)
        x0, x1 = max(0, x - CROP), min(scratch.shape[1], x + CROP)
        scratch[y0:y1, x0:x1] = -1.0
    return picks


def sheet(subj, rungs, y, x, tag, caption, note):
    """One horizontal contact sheet of the same window across rungs."""
    panels = []
    ref = None
    for vt, cap in rungs:
        p = HALO / "view" / f"{subj}__{vt}.tif"
        if not p.exists():
            print(f"    missing view {p.name}, skipping panel")
            continue
        a = tifffile.imread(p)
        if a.ndim == 2:
            a = np.dstack([a] * 3)
        crop = to_u8(a[y:y + CROP, x:x + CROP, :3])
        if ref is None:
            ref = crop.astype(np.int16)
            sub2 = "reference"
        else:
            diff = int(np.abs(crop.astype(np.int16) - ref).mean())
            sub2 = f"mean |delta| vs OFF = {diff} DN/255"
        panels.append(labelled(Image.fromarray(crop), cap, note, sub2))

    if not panels:
        return None
    w = sum(p.width for p in panels) + 8 * (len(panels) - 1)
    out = Image.new("RGB", (w, panels[0].height), (16, 16, 16))
    ox = 0
    for p in panels:
        out.paste(p, (ox, 0))
        ox += p.width + 8
    dst = OUT / f"{subj}__{tag}.png"
    out.save(dst)
    print(f"    wrote {dst.name}  ({out.width}x{out.height})")
    return dst


def to_view(y, x, va, g0):
    """Map a measure-grid top-left to a view-grid top-left, keeping the SAME
    scene centre. The view is a full-resolution demosaic and the measurement
    grid is binned 2x2, so a CROP-square in view coords covers half the scene a
    CROP-square in measure coords does; centring rather than scaling the corner
    keeps the crop on the feature the window was chosen for."""
    sy = va.shape[0] / g0.shape[0]
    sx = va.shape[1] / g0.shape[1]
    cy = (y + CROP / 2.0) * sy
    cx = (x + CROP / 2.0) * sx
    vy = int(round(cy - CROP / 2.0))
    vx = int(round(cx - CROP / 2.0))
    vy = max(0, min(va.shape[0] - CROP, vy))
    vx = max(0, min(va.shape[1] - CROP, vx))
    return vy, vx


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for subj, rungs in (("bee-3-cpl", BEE_LADDER),
                        ("flower-bud-with-background-fern-cpl", FERN_LADDER)):
        print(f"==== {subj} ====")
        p0 = HALO / "measure" / f"{subj}__H0.tif"
        if not p0.exists():
            print("  missing H0, skipping")
            continue
        g0 = S.green(p0)
        fg, tau = SH.foreground_mask(g0)
        d = ndimage.distance_transform_edt(~fg)
        treated = (~fg) & (d <= SH.YOKE) & (d > 0)
        orient, coh = SL.oriented_mask(g0)

        # The view renders are full-resolution sRGB; the linear measurement
        # renders are on the binned plane grid. Map window coordinates by the
        # measured ratio rather than assuming they match.
        vp = HALO / "view" / f"{subj}__H0.tif"
        va = tifffile.imread(vp)
        sy = va.shape[0] / g0.shape[0]
        sx = va.shape[1] / g0.shape[1]
        print(f"  measure {g0.shape}  view {va.shape[:2]}  scale {sy:.3f},{sx:.3f}")

        # ---- LB7: oriented fine structure, IN THE TREATED BAND -------------
        # `treated` is the background side of the silhouette, so the hairs and
        # claws the softening claim is about are the ones projecting off the
        # subject into the yoke. Oriented content ON the subject is never
        # touched by the correction and a crop there could only show a null.
        w_or = (orient & treated).astype(np.float64)
        pk = pick_window(w_or, g0.shape, 1)
        if pk:
            y, x, v = pk[0]
            vy, vx = to_view(y, x, va, g0)
            print(f"  oriented window at measure({y},{x}) -> view({vy},{vx})"
                  f"  coherence density {v:.3f}")
            sheet(subj, rungs, vy, vx, "ladder-ORIENTED-fine-structure",
                  "oriented", f"window chosen on OFF; coh>={SL.COH_MIN}")

        # ---- the silhouette edge, where the halo is scored ------------------
        w_edge = ((~fg) & (d >= 2.0) & (d <= 25.0)).astype(np.float64)
        fgf = ndimage.uniform_filter(fg.astype(np.float64), size=CROP,
                                     mode="constant", cval=0.0)
        half = CROP // 2
        vfg = fgf[half:g0.shape[0] - half, half:g0.shape[1] - half]
        integ = ndimage.uniform_filter(w_edge, size=CROP, mode="constant", cval=0.0)
        vv = integ[half:g0.shape[0] - half, half:g0.shape[1] - half].copy()
        vv[(vfg < 0.15) | (vfg > 0.70)] = -1.0
        idx = int(np.argmax(vv))
        y, x = np.unravel_index(idx, vv.shape)
        vy, vx = to_view(int(y), int(x), va, g0)
        print(f"  edge window at measure({y},{x}) -> view({vy},{vx})")
        sheet(subj, rungs, vy, vx, "ladder-SILHOUETTE-edge",
              "silhouette", "window chosen on OFF, richest in near-yoke bg")

    print(f"\nsheets in {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
