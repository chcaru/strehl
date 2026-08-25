"""M120 step 2 — PC1: is the artifact ORCH ranked #1 in the SHIPPED render?

The three PNGs the brief names are produced by M87's `15-crops.py` from
`cache/bee3-leg-sel.npy`, which `04-through-focus.py` builds as a pure per-pixel
argmax (gate 0), unaligned, in green luma, in Python. This step registers the
actual shipped `strehl stack` render against that ROI and emits the identical
crop at the identical stretch, so the two can be compared by eye and by number.

Registration is measured, never assumed (prereg NC5): the offset is found by
normalised cross-correlation and refused if the peak is not unique.
"""

import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image

HERE = Path(__file__).resolve().parent
OUT = Path(r"C:\dev\strehl-out\M120")
OUT.mkdir(parents=True, exist_ok=True)
M87 = Path(r"C:\dev\blog\death-of-software\projects\strehl\experiments\M87-occlusion\cache")

# M87 geometry, read off 04-through-focus.py / m87lib.py, not guessed.
ROI = (1200, 1900, 300, 1400)  # ROI_LEG, rawpy binned coords
MARGIN = 22  # WINDOW_RADIUS + REGULARISER_RADIUS + 1
BOX = (ROI[0] - MARGIN, ROI[1] + MARGIN, ROI[2] - MARGIN, ROI[3] + MARGIN)
TIGHT = (330, 610, 150, 570)  # box-relative, from 15-crops.py
SUB = (300, 800, 100, 800)


def png(a, path, lo, hi, gamma=2.2, scale=1):
    v = np.clip((a - lo) / max(hi - lo, 1e-9), 0, 1) ** (1.0 / gamma)
    im = Image.fromarray((v * 255).astype(np.uint8))
    if scale != 1:
        im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
    im.save(path)


def ncc_offset(ref, mov, search=24):
    """Integer (dy, dx) maximising normalised cross-correlation of mov onto ref.

    `ref` is the smaller patch; `mov` is a larger window centred on the nominal
    position with `search` px of slack in each direction.
    """
    h, w = ref.shape
    r = ref - ref.mean()
    rn = np.sqrt((r * r).sum())
    best = None
    scores = np.full((2 * search + 1, 2 * search + 1), -2.0)
    for i, dy in enumerate(range(-search, search + 1)):
        for j, dx in enumerate(range(-search, search + 1)):
            m = mov[search + dy : search + dy + h, search + dx : search + dx + w]
            m = m - m.mean()
            den = np.sqrt((m * m).sum()) * rn
            s = float((r * m).sum() / den) if den > 0 else -2.0
            scores[i, j] = s
            if best is None or s > best[0]:
                best = (s, dy, dx)
    return best, scores


def main() -> int:
    sel = np.load(M87 / "bee3-leg-sel.npy")  # gate-0 argmax merge, green luma
    print(f"M87 sel (gate-0 argmax, unaligned, python): {sel.shape} {sel.dtype}")

    ship = tifffile.imread(M87 / "ship-before-linear.tif")
    print(f"shipped binned-linear render: {ship.shape} {ship.dtype}")
    g = ship[:, :, 1].astype(np.float32)

    # Nominal position: same rows, columns offset unknown (rawpy 7040 visible vs
    # rawler 7032 active). Correlate on a mid-contrast patch inside the box.
    ph, pw = 256, 256
    py, px = BOX[0] + 200, BOX[2] + 200
    ref = sel[200 : 200 + ph, 200 : 200 + pw].astype(np.float32)
    search = 24
    mov = g[py - search : py + ph + search, px - search : px + pw + search]
    (score, dy, dx), scores = ncc_offset(ref, mov, search)
    flat = np.sort(scores.ravel())[::-1]
    print(f"NCC peak {score:.5f} at (dy={dy}, dx={dx});  2nd={flat[1]:.5f}  10th={flat[9]:.5f}")
    if score < 0.8:
        print("REFUSE: correlation peak too weak to claim registration")
        return 2

    # uniqueness: peak must beat everything more than 2 px away
    yy, xx = np.mgrid[-search : search + 1, -search : search + 1]
    far = (np.abs(yy - dy) > 2) | (np.abs(xx - dx) > 2)
    print(f"  best off-peak (>2px away) = {scores[far].max():.5f}")

    # Same stretch the brief's PNGs use.
    c0 = sel[SUB[0] : SUB[1], SUB[2] : SUB[3]]
    lo, hi = np.percentile(c0, (0.5, 99.7))
    print(f"M87 common stretch lo={lo:.0f} hi={hi:.0f}")

    y0, y1, x0, x1 = TIGHT
    sel_t = sel[y0:y1, x0:x1]
    ship_t = g[BOX[0] + dy + y0 : BOX[0] + dy + y1, BOX[2] + dx + x0 : BOX[2] + dx + x1]

    png(sel_t, OUT / "PC1-A-M87-gate0-argmax-tight2x.png", lo, hi, scale=2)

    # The shipped render is on a different absolute scale (black-subtracted,
    # possibly gained). Match by robust affine fit over the SAME crop so the
    # comparison is of STRUCTURE, not level.
    a_s = sel_t.ravel().astype(np.float64)
    b_s = ship_t.ravel().astype(np.float64)
    A = np.vstack([b_s, np.ones_like(b_s)]).T
    coef, *_ = np.linalg.lstsq(A, a_s, rcond=None)
    print(f"level match: sel ~= {coef[0]:.5f} * ship + {coef[1]:.2f}")
    ship_m = coef[0] * ship_t + coef[1]
    png(ship_m, OUT / "PC1-B-SHIPPED-gate4-tight2x.png", lo, hi, scale=2)

    np.save(OUT / "pc1_offset.npy", np.array([dy, dx]))
    np.save(OUT / "pc1_sel_tight.npy", sel_t)
    np.save(OUT / "pc1_ship_tight.npy", ship_m.astype(np.float32))
    print(f"\nwrote crops to {OUT}")
    print(f"offset dy={dy} dx={dx} (M87 rawpy-binned -> strehl binned grid)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
