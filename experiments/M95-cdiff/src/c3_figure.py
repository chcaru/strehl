"""M95 arm 7 -- the deliverable figure.

Four panels at 100%, identical crop, identical transfer, no panel resampled and
no sharpness number burned into any panel. The point is to let the eye rank the
arms without being told what to see, because the metric has already been wrong
once tonight in this project.

TRUTH is the ground truth the ladder scores against, so it is the ceiling rather
than another candidate.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[2] / "M95-demosaic" / "src"))
sys.path.insert(0, str(HERE.parent))

import m95dem as M  # noqa: E402
from c1_ladder import demosaic_cdiff  # noqa: E402
from c2_refine import demosaic_cdiff2  # noqa: E402

TRUTH = Path(r"C:\dev\strehl-out\M95-demosaic\scratch\truth_AHD.npy")
OUTDIR = Path(r"C:\dev\strehl-out\M95-cdiff")
CROP = 300


def main():
    T = np.load(TRUTH).astype(np.float32)
    mo = M.mosaic_rggb(T)

    # Crop on the truth's own in-band energy, so no candidate picks its ground.
    tiles = M.pick_tiles(T, CROP, 6, 0.30, 0.48, margin=CROP)
    y, x = tiles[0]
    print(f"crop at ({y}, {x}) size {CROP}, chosen on TRUTH energy")

    arms = [("TRUTH", None),
            ("MHC (shipped)", M.demosaic_mhc),
            ("CDIFF", demosaic_cdiff),
            ("CDIFF2", demosaic_cdiff2)]

    # One transfer for every panel, fixed from the truth crop alone.
    ref = T[y:y + CROP, x:x + CROP]
    lo, hi = float(np.percentile(ref, 1)), float(np.percentile(ref, 99.5))
    print(f"shared transfer: [{lo:.4f}, {hi:.4f}] then gamma 1/2.2")

    def enc(a):
        v = np.clip((a - lo) / max(hi - lo, 1e-6), 0.0, 1.0) ** (1 / 2.2)
        return (v * 255.0 + 0.5).astype(np.uint8)

    pad, label = 8, 26
    W = len(arms) * CROP + (len(arms) + 1) * pad
    H = CROP + 2 * pad + label
    sheet = Image.new("RGB", (W, H), (16, 16, 16))
    d = ImageDraw.Draw(sheet)

    for i, (name, f) in enumerate(arms):
        img = ref if f is None else f(mo)[y:y + CROP, x:x + CROP]
        px = pad + i * (CROP + pad)
        sheet.paste(Image.fromarray(enc(img)), (px, pad + label))
        d.text((px + 2, pad + 6), name, fill=(235, 235, 235))

    OUTDIR.mkdir(parents=True, exist_ok=True)
    out = OUTDIR / "M95-cdiff-panels.png"
    sheet.save(out)
    print(f"wrote {out}  {sheet.size[0]}x{sheet.size[1]}")

    # Chroma error maps: the thing CDIFF was built to fix, shown directly.
    # |reconstructed - truth| in R and B, same scale for every arm.
    lines = []
    for name, f in arms[1:]:
        dm = f(mo)[y:y + CROP, x:x + CROP]
        er = float(np.abs(dm[..., 0] - ref[..., 0]).mean())
        eg = float(np.abs(dm[..., 1] - ref[..., 1]).mean())
        eb = float(np.abs(dm[..., 2] - ref[..., 2]).mean())
        lines.append(f"  {name:<16} mean|err| in this crop   "
                     f"R {er:.5f}  G {eg:.5f}  B {eb:.5f}")
    print("\npixel error against truth in the crop shown "
          "(NOT the ladder metric, which is band-limited):")
    for ln in lines:
        print(ln)
    (OUTDIR / "panels.txt").write_text(
        f"crop ({y},{x}) size {CROP}\ntransfer [{lo:.4f},{hi:.4f}] gamma 1/2.2\n"
        + "\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
