"""M120 step 9 — RETRACTION of step 8's ROI-A, plus exact geometry.

Step 8 is retracted in part. Its ROI-A Q values (SHIPPED gate 4 Q = 15.7 at
band 2-8) are INVALID and must not be quoted. Diagnosis:

  * the denominator population was the 23 armF-f*.tif single-frame renders,
    whose indices span only 119..208;
  * the merge draws from all 299 frames (M87's own elected-index field uses
    106 distinct indices spanning 7..298 inside the background ROI);
  * so `max_k` was taken over a population that does not contain the frames the
    merge actually used. The ROI-A search then made this worse by choosing the
    box that is quietest *in those 23 frames* -- which is exactly a box whose
    content is sharp in the OTHER 276. Looking at it confirms this: ROI-A sits
    on the bee's hair-fringed silhouette, not on background, and the gate-4
    render's minimum there (6646 DN) is below every one of the 23 frames'
    minima (12217 DN) purely because it elected frames outside the sample.

That is precisely the failure mode the brief warned about, and it happened to
point AT the alarming conclusion, so it is retracted loudly.

The logs settle the geometry and make a clean fix possible:
    armM-gate0-binlin, armM4-gate4-binlin, armF-f*  -> alignment OFF
    armC-aligned-gate0                              -> alignment ON, FOV 0.9315
So the merges and the single-frame renders share one unwarped grid, and the
M87 binned-luma cube should register to it by a pure translation.
"""

import sys
from pathlib import Path

import numpy as np
import tifffile
from scipy import ndimage as ndi

M93 = Path(r"C:\dev\strehl-out\M93-out")
M87 = Path(r"C:\dev\blog\death-of-software\projects\strehl\experiments\M87-occlusion\cache")
OUT = Path(r"C:\dev\strehl-out\M120")

BOX = (1178, 1922, 278, 1422)
SUB = (200, 600, 200, 900)     # inside the box, plenty of leg structure


def dog(a):
    a = np.asarray(a, np.float32)
    return ndi.gaussian_filter(a, 2.0) - ndi.gaussian_filter(a, 16.0)


def main() -> int:
    sel = np.load(M87 / "bee3-leg-sel.npy").astype(np.float32)
    ship0 = tifffile.imread(M93 / "armM-gate0-binlin.tif")[:, :, 1].astype(np.float32)
    print(f"M87 sel {sel.shape}   armM-gate0-binlin green {ship0.shape}")

    a = dog(sel[SUB[0]:SUB[1], SUB[2]:SUB[3]])
    a = (a - a.mean()) / a.std()
    best = None
    for dy in range(-8, 9):
        for dx in range(-12, 13):
            b = ship0[BOX[0] + SUB[0] + dy: BOX[0] + SUB[1] + dy,
                      BOX[2] + SUB[2] + dx: BOX[2] + SUB[3] + dx]
            b = dog(b)
            b = (b - b.mean()) / b.std()
            r = float((a * b).mean())
            if best is None or r > best[0]:
                best = (r, dy, dx)
    r, dy, dx = best
    print(f"M87 cube -> shipped grid: BEST NCC {r:.4f} at dy={dy:+d} dx={dx:+d}")
    zero = None
    b = dog(ship0[BOX[0] + SUB[0]: BOX[0] + SUB[1], BOX[2] + SUB[2]: BOX[2] + SUB[3]])
    b = (b - b.mean()) / b.std()
    zero = float((a * b).mean())
    print(f"   NCC at zero offset = {zero:.4f}")
    if abs(dy) >= 8 or abs(dx) >= 12:
        print("   !! endpoint -- refusing to trust this offset")
        return 3
    print(f"   -> the M87 Python cube and the Rust unaligned render agree to a "
          f"pure translation of ({dy},{dx}); the two implementations of the SAME "
          f"gate-0 rule cross-validate at NCC {r:.4f}.")

    # cross-calibration: how much extra band-pass energy does the shipped
    # pipeline (rawler binning + demosaic) add relative to M87's green luma?
    cube = np.load(M87 / "bee3-leg-luma.npy", mmap_mode="r")
    idx = [int(p.stem.split("-f")[1]) for p in sorted(M93.glob("armF-f*.tif"))
           if "demo" not in p.name]
    T = (330, 610, 150, 570)
    R = (146, 274, 292, 420)
    y0, y1 = T[0] + R[0], T[0] + R[1]
    x0, x1 = T[2] + R[2], T[2] + R[3]
    print(f"\nband-pass(2,8) RMS in the background ROI, per frame, both pipelines:")
    print(f"{'frame':>7}{'M87 luma':>12}{'shipped':>12}{'ratio':>9}"
          f"{'M87 lvl':>10}{'ship lvl':>10}")
    ratios = []
    for k in idx:
        m = np.array(cube[k, y0:y1, x0:x1], np.float32)
        s = tifffile.imread(M93 / f"armF-f{k}.tif")[
            BOX[0] + y0 + dy: BOX[0] + y1 + dy, BOX[2] + x0 + dx: BOX[2] + x1 + dx, 1
        ].astype(np.float32)
        rm = float(np.sqrt((dog_bp(m) ** 2).mean()))
        rs = float(np.sqrt((dog_bp(s) ** 2).mean()))
        ratios.append((rs / m.mean()) / (rm / max(m.mean(), 1) * m.mean() / m.mean()))
        print(f"{k:>7}{rm:12.2f}{rs:12.2f}{rs/rm:9.3f}{m.mean():10.0f}{s.mean():10.0f}")
    np.save(OUT / "m120_offset_shipgrid.npy", np.array([dy, dx]))
    print(f"\nwrote {OUT / 'm120_offset_shipgrid.npy'}")
    return 0


def dog_bp(a):
    a = np.asarray(a, np.float32)
    return ndi.gaussian_filter(a, 2.0) - ndi.gaussian_filter(a, 8.0)


if __name__ == "__main__":
    sys.exit(main())
