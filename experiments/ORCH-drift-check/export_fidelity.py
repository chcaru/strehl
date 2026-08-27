"""Is the viewable export bit-exact, or would he be judging the encoder?

Three of my instruments failed tonight by corrupting the thing they measured.
Handing over an 8-bit export as a print-evaluation artifact makes the encoder
part of the verdict.

The first export used JPEG q98 4:4:4 and failed a tolerance registered before
the run (max 10-12 DN, mean 0.82-1.28 DN across the five highest-detail
subjects). The export was changed to PNG rather than the tolerance being
loosened, so this check now demands EXACT equality: any non-zero difference
means the encoder is contributing to what he sees.
"""
import pathlib, numpy as np, tifffile
from PIL import Image

SRC = pathlib.Path(r"C:\dev\strehl-out\acceptance\SHIP-V4")
DST = pathlib.Path(r"C:\dev\strehl-out\DELIVER-V5\full-resolution")

# the highest-detail subjects = where an encoder is most likely to be caught.
SUBJECTS = ["leaf-2-cpl", "112MSDCF", "lead-1-cpl", "flat-on-ruler-cpl", "tweezers-cpl"]


def to8(a):
    return np.clip(np.asarray(a, dtype=np.float64) / 257.0, 0.0, 255.0).round().astype(np.uint8)


rows, bad, missing = [], 0, 0
print("requirement: max error EXACTLY 0 DN -- the export must be the master.\n")
print(f"{'subject':<24} {'max err':>8} {'mean err':>9} {'diff px':>12}  verdict")
print("-" * 70)
for s in SUBJECTS:
    m = SRC / f"{s}--SHIP-V4.tiff"
    j = DST / f"{s}.png"
    if not m.exists() or not j.exists():
        print(f"{s:<24} {'MISSING':>8}  {'master' if not m.exists() else 'export'}")
        missing += 1
        continue
    ref = to8(tifffile.imread(str(m))[:, :, :3]).astype(np.int16)
    got = np.asarray(Image.open(j).convert("RGB"), dtype=np.int16)
    if ref.shape != got.shape:
        print(f"{s:<24} SHAPE {ref.shape} vs {got.shape}")
        bad += 1
        continue
    d = np.abs(ref - got)
    mx, mean, npx = float(d.max()), float(d.mean()), int((d != 0).sum())
    ok = mx == 0.0
    bad += 0 if ok else 1
    rows.append((s, mx, mean, npx, ok))
    print(f"{s:<24} {mx:>8.0f} {mean:>9.4f} {npx:>12,}  {'exact' if ok else 'ENCODER PRESENT'}")

print("-" * 70)
print(f"examined : {len(rows)}")
print(f"exact    : {len(rows) - bad}")
print(f"inexact  : {bad}")
print(f"missing  : {missing}")
print(f"total    : {len(rows) + missing}  (requested {len(SUBJECTS)})")
if len(rows) + missing != len(SUBJECTS):
    raise SystemExit("PARTITION BROKEN")
if missing:
    raise SystemExit("a requested subject was not examined -- that is not a pass")
print()
print("VERDICT: bit-exact -- what he sees IS the master, at 8 bits per channel."
      if bad == 0 else
      "VERDICT: the encoder is part of the picture. Do not judge print quality on these.")

