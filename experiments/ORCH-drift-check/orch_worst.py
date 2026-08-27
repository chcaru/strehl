"""Adversarial QA: crop each master at its own worst edge-overshoot site.

The gallery's 1:1 crops are chosen for interest, not for damage, so a clean sweep over them
is a favourable sample and cannot support a print-readiness claim. This picks, per master,
the single edge site with the largest normalised overshoot -- the most artifact-like place
in that image on the metric's own terms -- and assembles them into one sheet.

If the worst site in every master looks acceptable, that is a much stronger statement than
twenty-six pleasant crops. If a real artifact exists anywhere, this is where it surfaces.

Display gain is one stated constant per master (0.2/99.8 percentile of that master), printed
with the clipped fraction, because a per-crop percentile stretch makes severity
incomparable between crops -- measured earlier at up to 29x bias, running the wrong way.
"""
import pathlib
import sys

import numpy as np
import tifffile

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from orch_contact import COLS, LABEL_H, draw_text, png_rgb  # noqa: E402
from orch_halo import DS, downsample, edge_points, robust_step  # noqa: E402
from orch_halosite import site_overshoots  # noqa: E402

SRC = pathlib.Path(r"C:\dev\strehl-out\SHIP-V2")
OUT = pathlib.Path(r"C:\dev\strehl-out\ORCH-CONTACT")
CROP = 360


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    paths = [p for p in sorted(SRC.iterdir()) if p.suffix.lower() == ".tiff"]
    print(f"{len(paths)} masters in {SRC}\n")
    rng = np.random.default_rng(7)
    tiles, names = [], []

    print(f"{'master':40s} {'worst':>8s} {'x':>6s} {'y':>6s} {'clip%':>7s}")
    for p in paths:
        a = tifffile.imread(str(p))
        rgb = a[:, :, :3]
        del a
        lum = (0.2126 * rgb[:, :, 0] + 0.7152 * rgb[:, :, 1]
               + 0.0722 * rgb[:, :, 2]).astype(np.float32)
        img = downsample(lum, DS).astype(np.float32)
        del lum
        ms = robust_step(img)
        pts, gy, gx, _ = edge_points(img, rng)
        sites = site_overshoots(img, pts, gy, gx, ms)
        nm = p.stem.replace("--SHIP-V2", "")
        if not sites:
            print(f"{nm:40s} {'-':>8s}  no site passed the gates")
            del rgb
            continue
        ov, py, px, _, _, _ = sites[0]

        lo = float(np.percentile(rgb[::8, ::8], 0.2))
        hi = float(np.percentile(rgb[::8, ::8], 99.8))
        H, W, _ = rgb.shape
        y0 = int(np.clip(py * DS - CROP // 2, 0, H - CROP))
        x0 = int(np.clip(px * DS - CROP // 2, 0, W - CROP))
        blk = rgb[y0:y0 + CROP, x0:x0 + CROP].astype(np.float32)
        clip = float(((blk < lo) | (blk > hi)).mean())
        v = np.clip((blk - lo) * (255.0 / max(hi - lo, 1.0)), 0, 255).astype(np.uint8)
        tiles.append(v)
        names.append(f"{nm} {ov:.2f}")
        print(f"{nm:40s} {ov:8.3f} {px * DS:6d} {py * DS:6d} {100 * clip:7.2f}")
        del rgb

    if not tiles:
        print("no tiles")
        return 1
    rows = (len(tiles) + COLS - 1) // COLS
    cell_h = CROP + LABEL_H
    sheet = np.zeros((rows * cell_h, COLS * CROP, 3), dtype=np.uint8)
    for i, (t, nm) in enumerate(zip(tiles, names)):
        r, c = divmod(i, COLS)
        y0, x0 = r * cell_h, c * CROP
        sheet[y0:y0 + CROP, x0:x0 + CROP] = t
        draw_text(sheet[y0 + CROP:y0 + cell_h, x0:x0 + CROP], f"{i:02d} {nm}"[:58], 3, 2)
    out = OUT / "contact-sheet-worst.png"
    png_rgb(sheet, out)
    print(f"\n{len(tiles)} worst-site crops, {sheet.shape[1]}x{sheet.shape[0]}")
    print(f"-> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
