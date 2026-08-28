"""DELIVER-V6: fixed-coordinate 1:1 before/after crops for the lateral-CA re-fit.

WHAT THIS IS FOR
----------------
`optics.rs:461` now reads `eps_r = -508.4e-6`. Every master in
`C:\\dev\\strehl-out\\ORCH-FAITHFUL\\faithful\\` predates it and carries the old
+704.5 ppm coefficient, which BUILD-CROP diagnosed as over-correcting red by
~40%: it takes red from -2.009 px (inward) PAST ZERO to +0.672 px (outward)
while blue stays outward, so R and B pile up on the SAME side of every edge and
the fringe pair becomes one coherent MAGENTA fringe (BUILD-CROP 14.4).

The owner has never seen a frame with the fix in it. This puts old and new side
by side at native resolution so he can look.

DESIGN RULES, each one a mistake this project has already made
-------------------------------------------------------------
* **Fixed coordinates.** The site is chosen once, on the OLD master, and the
  SAME (y, x) is cut from both. Re-choosing per arm lets each arm show its own
  best region, which is how a comparison lies (M110-sheet constraint 3).

* **Chosen on the OLD master, deliberately.** The question is "was the thing
  that was broken fixed", so the sites are the places the defect was, not the
  places the new render looks good. Choosing on the new master would be
  choosing the answer. Stated so it can be argued with.

* **ONE display transform, from the OLD master, applied identically to both.**
  Per-arm autoscaling fabricates differences between images that do not differ
  (AGENTS rule 48). The transform is the committed one from
  `experiments/ORCH-drift-check/orch_corpuseye.py`: scale by 1/p99.9 of luma,
  clip, then **(1/2.2). Verified to reproduce ORCH-EYE `sheet-00`'s
  `113MSDCF [texture] y=1156 x=3852` tile from the old master; the no-gamma
  variant does not match, which is what proves the masters are linear.

* **1:1, no resampling, ever.** Crops are pixel copies. Nothing here resizes,
  magnifies, or interpolates. AGENTS rule 48 measured that a visual verdict is
  only valid on an image the viewer shows without resampling -- about 400 px --
  so CROP is 360, and each arm is written as its OWN standalone file at 360 px
  as well as into the joined pair. The joined pair is 2x360 wide and is for the
  owner's monitor; the single-arm files are what a verdict may be pronounced on.

* **Radius floor.** Lateral CA vanishes at the optical centre, so a near-centre
  site measures noise. Sites must sit beyond 0.55 of the half-diagonal.

* **Absolute floors, not a ranking.** A top-N picker returns background on a
  low-texture subject and manufactures a verdict. A site must clear an absolute
  edge-gradient floor AND an absolute chroma-excursion floor; a subject with too
  few qualifying sites is reported UNSCORED, never clean.

WHAT IT DOES NOT DO
-------------------
It computes no score and issues no verdict. V-REVIEW owns the independent
metric (`experiments/V-REVIEW/PREREG-v6ca.md`) and deliberately does not use any
estimator from the lane that fitted the coefficient. This tool only puts honest
pixels side by side.

Usage:
    python caab.py <old-dir> <new-dir> <out-dir> [--crop 360] [--sites 3]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image, ImageDraw

CROP_DEFAULT = 360          # <= the ~400 px viewer resampling floor (rule 48)
GAP = 10
LABEL_H = 22
STRIDE = 16

# Absolute floors. In DN on the 16-bit master, so they do not move with content.
GRAD_FLOOR = 900.0          # edge must be a real edge
CHROMA_FLOOR = 260.0        # magenta-axis excursion must be real
RADIUS_FRAC = 0.55          # lateral CA vanishes at the centre


def to_luma(a: np.ndarray) -> np.ndarray:
    return 0.2126 * a[:, :, 0] + 0.7152 * a[:, :, 1] + 0.0722 * a[:, :, 2]


def box(a: np.ndarray, r: int) -> np.ndarray:
    pad = np.pad(a, r + 1, mode="edge")
    c = pad.cumsum(0).cumsum(1)
    w = 2 * r + 1
    s = c[w:, w:] - c[:-w, w:] - c[w:, :-w] + c[:-w, :-w]
    return s[: a.shape[0], : a.shape[1]] / (w * w)


def site_scores(a: np.ndarray):
    """(edge strength, magenta-axis excursion) on a strided grid, in DN.

    The magenta axis is `((R-G) + (B-G)) / 2`. It is deliberately the SIGNED
    joint departure of red and blue from green, because that is the shape the
    over-correction makes: natural lateral CA moves R and B in OPPOSITE
    directions and largely cancels on this axis, while the over-corrected
    fringe moves them together and adds. Its local peak-to-trough across an
    edge is what the eye reads as a magenta rim.
    """
    f = a.astype(np.float32)
    luma = to_luma(f)
    mag = 0.5 * ((f[:, :, 0] - f[:, :, 1]) + (f[:, :, 2] - f[:, :, 1]))

    small = luma[::STRIDE, ::STRIDE]
    gy, gx = np.gradient(small)
    grad = np.hypot(gy, gx)

    ms = mag[::STRIDE, ::STRIDE]
    # peak-to-trough of the magenta axis in a small neighbourhood
    excursion = box(np.abs(ms - box(ms, 6)), 3)
    return grad, excursion


def pick_sites(a: np.ndarray, size: int, n: int):
    """Qualifying sites as (y, x) top-left corners, best first."""
    h, w = a.shape[:2]
    grad, exc = site_scores(a)
    gh, gw = grad.shape

    cy, cx = h / 2.0, w / 2.0
    rmax = np.hypot(cy, cx)
    yy = (np.arange(gh) * STRIDE - cy)[:, None]
    xx = (np.arange(gw) * STRIDE - cx)[None, :]
    radius = np.hypot(yy, xx) / rmax

    ok = (grad >= GRAD_FLOOR) & (exc >= CHROMA_FLOOR) & (radius >= RADIUS_FRAC)

    half = size // (2 * STRIDE)
    ok[:half, :] = False
    ok[-half:, :] = False
    ok[:, :half] = False
    ok[:, -half:] = False

    score = np.where(ok, grad * exc, 0.0)
    sep = max(size // STRIDE, 20)

    out, taken = [], []
    for idx in np.argsort(score, axis=None)[::-1]:
        if len(out) >= n:
            break
        sy, sx = np.unravel_index(idx, score.shape)
        if score[sy, sx] <= 0:
            break
        if any(abs(sy - ty) < sep and abs(sx - tx) < sep for ty, tx in taken):
            continue
        taken.append((sy, sx))
        y = max(0, min(h - size, int(sy * STRIDE) - size // 2))
        x = max(0, min(w - size, int(sx * STRIDE) - size // 2))
        out.append(
            dict(y=y, x=x, grad=float(grad[sy, sx]), chroma=float(exc[sy, sx]),
                 radius=float(radius[sy, sx]))
        )
    return out


def render_crop(a: np.ndarray, y: int, x: int, size: int, scale: float) -> np.ndarray:
    c = a[y : y + size, x : x + size, :3].astype(np.float32) * scale
    return (np.clip(c, 0.0, 1.0) ** (1.0 / 2.2) * 255.0 + 0.5).astype(np.uint8)


def join(old_t: np.ndarray, new_t: np.ndarray, size: int, label: str) -> Image.Image:
    w = 2 * size + 3 * GAP
    h = size + LABEL_H + 2 * GAP
    sheet = np.full((h, w, 3), 28, np.uint8)
    sheet[GAP + LABEL_H : GAP + LABEL_H + size, GAP : GAP + size] = old_t
    sheet[GAP + LABEL_H : GAP + LABEL_H + size, 2 * GAP + size : 2 * GAP + 2 * size] = new_t
    img = Image.fromarray(sheet)
    d = ImageDraw.Draw(img)
    d.text((GAP + 2, 4), label, fill=(235, 235, 235))
    d.text((GAP + 2, GAP + LABEL_H - 14), "OLD  eps_r=-704.5e-6", fill=(255, 190, 190))
    d.text((2 * GAP + size + 2, GAP + LABEL_H - 14), "NEW  eps_r=-508.4e-6", fill=(190, 255, 190))
    return img


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("old_dir")
    ap.add_argument("new_dir")
    ap.add_argument("out_dir")
    ap.add_argument("--crop", type=int, default=CROP_DEFAULT)
    ap.add_argument("--sites", type=int, default=3)
    ap.add_argument("--subject", action="append", default=None)
    args = ap.parse_args()

    old_dir, new_dir = Path(args.old_dir), Path(args.new_dir)
    dst = Path(args.out_dir)
    dst.mkdir(parents=True, exist_ok=True)
    (dst / "arms").mkdir(exist_ok=True)

    names = args.subject or sorted(p.stem for p in old_dir.glob("*.tiff"))
    report = []
    unscored = []

    for name in names:
        po, pn = old_dir / f"{name}.tiff", new_dir / f"{name}.tiff"
        if not pn.exists():
            print(f"SKIP     {name}: no new master")
            unscored.append((name, "no new master"))
            continue
        ao = tifffile.imread(str(po))[:, :, :3]
        an = tifffile.imread(str(pn))[:, :, :3]
        if ao.shape != an.shape:
            print(f"CONFOUND {name}: geometry moved {ao.shape} -> {an.shape}")
            unscored.append((name, f"geometry moved {ao.shape} -> {an.shape}"))
            continue

        # ONE transform, from the OLD master, used for BOTH arms.
        scale = 1.0 / max(float(np.percentile(to_luma(ao.astype(np.float32)), 99.9)), 1.0)

        sites = pick_sites(ao, args.crop, args.sites)
        if not sites:
            print(f"UNSCORED {name}: no site clears the absolute floors")
            unscored.append((name, "no site clears grad/chroma/radius floors"))
            continue

        for i, s in enumerate(sites):
            y, x = s["y"], s["x"]
            to = render_crop(ao, y, x, args.crop, scale)
            tn = render_crop(an, y, x, args.crop, scale)
            lab = f"{name}  site{i}  y={y} x={x}  r={s['radius']:.2f}"
            join(to, tn, args.crop, lab).save(str(dst / f"{name}-site{i}.jpg"), quality=96)
            Image.fromarray(to).save(str(dst / "arms" / f"{name}-site{i}-OLD.png"))
            Image.fromarray(tn).save(str(dst / "arms" / f"{name}-site{i}-NEW.png"))
            report.append(dict(subject=name, site=i, y=y, x=x, **{
                k: s[k] for k in ("grad", "chroma", "radius")}))
        print(f"ok       {name}: {len(sites)} site(s)")

    (dst / "sites.json").write_text(json.dumps(
        dict(crop=args.crop, stride=STRIDE, grad_floor=GRAD_FLOOR,
             chroma_floor=CHROMA_FLOOR, radius_frac=RADIUS_FRAC,
             sites=report, unscored=unscored), indent=2))
    print()
    print(f"SUMMARY  {len(names)} subjects, {len(report)} pairs, {len(unscored)} unscored")
    for n, why in unscored:
        print(f"         UNSCORED {n}: {why}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
