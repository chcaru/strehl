"""M120 step 5 — R3: is the patchwork in the INPUT FRAMES?

The one that would embarrass us most if we missed it. Renders the same TIGHT
crop ORCH judged, from single unmerged input frames, at the identical M87
stretch, plus their band-pass maps. Also reports which frames the background
actually elects, so the frames shown are the ones that matter.
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

M87 = Path(r"C:\dev\blog\death-of-software\projects\strehl\experiments\M87-occlusion\cache")
OUT = Path(r"C:\dev\strehl-out\M120")
(OUT / "inputs").mkdir(parents=True, exist_ok=True)

TIGHT = (330, 610, 150, 570)
LO, HI = 176.0, 3680.0        # the exact M87 stretch used for the brief's PNGs


def stretch(a):
    v = (np.clip(a, LO, HI) - LO) / (HI - LO)
    return (255.0 * np.power(v, 1.0 / 2.2) + 0.5).astype(np.uint8)


def up2(a):
    return np.kron(a, np.ones((2, 2), np.uint8))


def main() -> int:
    y0, y1, x0, x1 = TIGHT
    arg = np.load(M87 / "bee3-leg-argbest.npy")[y0:y1, x0:x1]
    cube = np.load(M87 / "bee3-leg-luma.npy", mmap_mode="r")
    n = cube.shape[0]

    # background half of the crop, defined without reference to the merge:
    # the columns to the right of the leg. Use the frame-median image to find
    # the bright backdrop.
    med = np.array(cube[n // 2, y0:y1, x0:x1], np.float32)
    bright = med > np.percentile(med, 60)
    idx, cnt = np.unique(arg[bright], return_counts=True)
    order = np.argsort(-cnt)[:12]
    print("frames elected over the bright (background) part of the TIGHT crop:")
    for i in order:
        print(f"   frame {idx[i]:3d}  {100.0 * cnt[i] / bright.sum():5.2f}% of background px")
    top = [int(idx[i]) for i in order[:6]]

    show = sorted(set(top + [0, n // 4, n // 2, 3 * n // 4, n - 1]))
    print(f"\nrendering {len(show)} single input frames: {show}")

    tiles, bptiles = [], []
    for k in show:
        f = np.array(cube[k, y0:y1, x0:x1], np.float32)
        Image.fromarray(up2(stretch(f))).save(OUT / "inputs" / f"frame-{k:03d}.png")
        tiles.append(stretch(f))
        bp = ndi.gaussian_filter(f, 3.0) - ndi.gaussian_filter(f, 24.0)
        b = np.clip(128.0 + bp * 4.0, 0, 255).astype(np.uint8)
        bptiles.append(b)
        print(f"  frame {k:3d}: mean {f.mean():7.1f} DN   band-pass RMS {bp.std():6.2f} DN")

    def sheet(ts, path, cols=4):
        h, w = ts[0].shape
        rows = (len(ts) + cols - 1) // cols
        s = np.zeros((rows * (h + 6), cols * (w + 6)), np.uint8)
        for i, t in enumerate(ts):
            r, c = divmod(i, cols)
            s[r * (h + 6): r * (h + 6) + h, c * (w + 6): c * (w + 6) + w] = t
        Image.fromarray(s).save(path)
        print(f"wrote {path}  {s.shape}")

    sheet(tiles, OUT / "R3-input-frames-sheet.png")
    sheet(bptiles, OUT / "R3-input-frames-bandpass-sheet.png")

    # and the merge, same stretch, same crop, for side-by-side
    for name, fn in (("gate0-sel", "bee3-leg-sel.npy"), ("gate2", "bee3-leg-g2.npy")):
        a = np.load(M87 / fn)[y0:y1, x0:x1].astype(np.float32)
        Image.fromarray(up2(stretch(a))).save(OUT / "inputs" / f"MERGE-{name}.png")
        bp = ndi.gaussian_filter(a, 3.0) - ndi.gaussian_filter(a, 24.0)
        Image.fromarray(up2(np.clip(128.0 + bp * 4.0, 0, 255).astype(np.uint8))).save(
            OUT / "inputs" / f"MERGE-{name}-bandpass.png")
        print(f"  MERGE {name}: mean {a.mean():7.1f} DN   band-pass RMS {bp.std():6.2f} DN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
