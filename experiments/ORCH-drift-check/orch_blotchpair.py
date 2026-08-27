"""Render the exact windows the blotch detector flagged, master beside source frame.

§98's rule was to report both terms of a ratio. The corpus run then flagged three subjects
with elevated band power -- but two of them also read the master as NOISIER than a single
source frame, which a merge of a hundred frames cannot do. A reading that requires an
impossible mechanism is a reading to look at, not to publish.

Same window, same stated display gain, master left and source right, so the eye can settle
what the statistic cannot.
"""
import pathlib
import sys

import numpy as np
import rawpy
import tifffile

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from orch_blotch import WIN, lum_of  # noqa: E402
from orch_contact import LABEL_H, draw_text, png_rgb  # noqa: E402

SHIP = pathlib.Path(r"C:\dev\strehl-out\SHIP-V2")
RAW = pathlib.Path(r"D:\personal\macro")
OUT = pathlib.Path(r"C:\dev\strehl-out\ORCH-CONTACT")

# (subject, x, y) exactly as the corpus blotch run reported them.
SITES = [
    ("flowers-cpl", 4358, 3206),
    ("flower-inner-edge-cpl", 3150, 3678),
    ("flat-on-ruler-cpl", 2238, 3758),
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    panels, labels = [], []
    for nm, x, y in SITES:
        mp = SHIP / f"{nm}--SHIP-V2.tiff"
        if not mp.exists():
            print(f"{nm}: no master at {mp}")
            continue
        a = tifffile.imread(str(mp))
        mrgb = a[:, :, :3][y:y + WIN, x:x + WIN].astype(np.float32)
        del a

        d = RAW / nm
        raws = sorted(q for q in d.iterdir() if q.suffix.lower() == ".arw")
        mid = raws[len(raws) // 2]
        with rawpy.imread(str(mid)) as rr:
            srgb_full = rr.postprocess(gamma=(1, 1), no_auto_bright=True,
                                       output_bps=16, use_camera_wb=True)
        srgb = srgb_full[y:y + WIN, x:x + WIN].astype(np.float32)
        del srgb_full

        # One window for both panels: severity must be comparable across the pair.
        both = np.concatenate([mrgb.ravel()[::37], srgb.ravel()[::37]])
        lo = float(np.percentile(both, 0.5))
        hi = float(np.percentile(both, 99.5))
        g = 255.0 / max(hi - lo, 1.0)
        mv = np.clip((mrgb - lo) * g, 0, 255).astype(np.uint8)
        sv = np.clip((srgb - lo) * g, 0, 255).astype(np.uint8)
        print(f"{nm:36s} window {lo:8.0f}..{hi:8.0f} DN  gain {g:.5f} lev/DN")
        print(f"{'':36s} master mean {float(mrgb.mean()):8.1f}   "
              f"source mean {float(srgb.mean()):8.1f}   "
              f"ratio {float(mrgb.mean()) / max(float(srgb.mean()), 1e-6):.3f}")
        panels.append(np.concatenate([mv, sv], axis=1))
        labels.append(f"{nm}  x{x} y{y}   LEFT MASTER   RIGHT SOURCE FRAME {mid.stem}")
        del mrgb, srgb

    if not panels:
        return 1
    cell_h = WIN + LABEL_H
    sheet = np.zeros((len(panels) * cell_h, 2 * WIN, 3), dtype=np.uint8)
    for i, (p, lab) in enumerate(zip(panels, labels)):
        sheet[i * cell_h:i * cell_h + WIN] = p
        draw_text(sheet[i * cell_h + WIN:(i + 1) * cell_h], lab[:280], 3, 2)
    out = OUT / "blotch-pairs.png"
    png_rgb(sheet, out)
    print(f"\n-> {out}  ({sheet.shape[1]}x{sheet.shape[0]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
