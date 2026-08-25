"""M120 step 13 — PIL 16-bit RGB hazard audit (ORCH fleet-wide alert).

Two questions, both answered by measurement rather than by argument:

  (1) Did M120 ever read a TIFF through PIL?  -- grep says no; this re-checks by
      reading every TIFF M120 consumed BOTH ways and reporting the divergence.
  (2) Second-order: were any files M120 CONSUMED produced by a PIL-laundered
      upstream? A 16-bit RGB TIFF carrying <= 256 distinct levels per channel
      has been through an 8-bit reader somewhere. This matters most for
      `ship-before-linear.tif`, the file behind M120's own retracted claim.
"""

import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image

M87 = Path(r"C:\dev\blog\death-of-software\projects\strehl\experiments\M87-occlusion\cache")
M93 = Path(r"C:\dev\strehl-out\M93-out")
SO = Path(r"C:\dev\strehl-out")

FILES = [
    M87 / "ship-before-linear.tif",
    M93 / "armM-gate0-binlin.tif",
    M93 / "armM4-gate4-binlin.tif",
    M93 / "armM-gate0-binlin-REPEAT.tif",
    M93 / "armC-aligned-gate0.tif",
    M93 / "armF-f145.tif",
    M93 / "armF-f173.tif",
    SO / "bee3-full.tif",
    SO / "bee3-g0.tif",
    SO / "bee3-g1.tif",
    SO / "ORCH-morning" / "bee-3-strehl.tif",
]


def main() -> int:
    print(f"{'file':34s}{'tifffile dtype':>16}{'PIL mode':>10}{'PIL dtype':>11}"
          f"{'levels/ch':>11}{'laundered?':>12}")
    bad = []
    for p in FILES:
        if not p.exists():
            print(f"{p.name:34s}{'MISSING':>16}")
            continue
        a = tifffile.imread(p)
        # a representative 512x512 patch keeps this cheap on the full-res file
        y = min(1600, a.shape[0] - 512)
        x = min(700, a.shape[1] - 512)
        patch = a[y:y + 512, x:x + 512]
        lv = int(np.unique(patch[..., 1] if patch.ndim == 3 else patch).size)
        with Image.open(p) as im:
            mode = im.mode
            pa = np.asarray(im)
        lau = "YES <-- " if lv <= 256 else "no"
        if lv <= 256:
            bad.append(p)
        print(f"{p.name:34s}{str(a.dtype):>16}{mode:>10}{str(pa.dtype):>11}"
              f"{lv:>11}{lau:>12}")
        del a, pa

    print("\n--- the hazard, reproduced on a project file (green channel) ---")
    p = M93 / "armM4-gate4-binlin.tif"
    t = tifffile.imread(p)[1654:1782, 720:848, 1].astype(np.float64)
    with Image.open(p) as im:
        pil = np.asarray(im)[1654:1782, 720:848, 1].astype(np.float64)
    print(f"  tifffile: dtype uint16  min {t.min():.0f} max {t.max():.0f} "
          f"sd {t.std():.2f}  distinct {np.unique(t).size}")
    print(f"  PIL     : dtype {np.asarray(pil).dtype}     min {pil.min():.0f} "
          f"max {pil.max():.0f}  sd {pil.std():.2f}  distinct {np.unique(pil).size}")
    print(f"  -> PIL loses {np.unique(t).size / max(np.unique(pil).size,1):.0f}x "
          f"of the level resolution in M120's own ROI")

    # what Q would M120 have reported off a PIL read?
    from scipy import ndimage as ndi

    def C(a):
        a = np.asarray(a, np.float32)
        return float(np.sqrt(((ndi.gaussian_filter(a, 2.0) - ndi.gaussian_filter(a, 8.0)) ** 2).mean()) / a.mean())

    cube = np.load(M87 / "bee3-leg-luma.npy", mmap_mode="r")
    den = max(C(np.array(cube[k, 476:604, 442:570], np.float32)) for k in range(cube.shape[0]))
    print(f"\n  Q(2-8) of the SHIPPED default via tifffile = {C(t)/den:.3f}   <- reported")
    print(f"  Q(2-8) of the SHIPPED default via PIL      = {C(pil)/den:.3f}   <- would have been")

    print(f"\n{len(bad)} of {len(FILES)} files show <=256 distinct levels "
          f"(i.e. PIL-laundered upstream): {[b.name for b in bad] or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
