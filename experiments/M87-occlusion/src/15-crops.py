"""M87 step 15 -- before/after crops, the deliverable the owner will look at.

Writes 8-bit PNG crops on ONE common stretch (computed from F0 alone, so no arm
can flatter itself with its own normalisation) into

    C:\\dev\\strehl-out\\M87-before-after\\

plus a placebo pair from a region with no occluding edge, which must be
pixel-identical.
"""

import pathlib
import shutil
import sys

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

OUT = pathlib.Path(__file__).resolve().parents[1] / "out"
CACHE = pathlib.Path(__file__).resolve().parents[1] / "cache"
DEST = pathlib.Path(r"C:\dev\strehl-out\M87-before-after")
DEST.mkdir(parents=True, exist_ok=True)

SUB = (300, 800, 100, 800)
TIGHT = (330, 610, 150, 570)
MARGIN = 22


def png(a, path, lo, hi, gamma=2.2, scale=1):
    v = np.clip((a - lo) / max(hi - lo, 1e-9), 0, 1) ** (1.0 / gamma)
    im = Image.fromarray((v * 255).astype(np.uint8))
    if scale != 1:
        im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
    im.save(path)


def main():
    sel = np.load(CACHE / "bee3-leg-sel.npy")
    mask = np.load(CACHE / "bee3-leg-mask.npy")
    arms = {
        "00-BEFORE-shipped-merge": sel,
        "01-AFTER-F1-mode-partition-d40": np.load(CACHE / "14-F1-mode-partition-d40.npy"),
        "02-AFTER-F1-mode-partition-d80": np.load(CACHE / "14-F1-mode-partition-d80.npy"),
        "03-AFTER-F3b-rank-consistent": np.load(CACHE / "14-F3b-median-band-only.npy"),
        "04-AFTER-F2-two-layer-unmix": np.load(CACHE / "13-F2.npy"),
        "05-BROKEN-F2-swapped-layers": np.load(CACHE / "13-F2-break-swap.npy"),
    }
    c0 = sel[SUB[0]:SUB[1], SUB[2]:SUB[3]]
    lo, hi = np.percentile(c0, (0.5, 99.7))
    print(f"common stretch lo={lo:.0f} hi={hi:.0f}")

    for tag, img in arms.items():
        png(img[SUB[0]:SUB[1], SUB[2]:SUB[3]], DEST / f"{tag}.png", lo, hi)
        png(img[TIGHT[0]:TIGHT[1], TIGHT[2]:TIGHT[3]],
            DEST / f"{tag}-tight2x.png", lo, hi, scale=2)
        print(f"  wrote {tag}")

    # ---- placebo: a region with no occluding edge -------------------------
    dist = ndi.distance_transform_edt(~mask)
    dist[:MARGIN + 90] = 0
    dist[-(MARGIN + 90):] = 0
    dist[:, :MARGIN + 90] = 0
    dist[:, -(MARGIN + 90):] = 0
    cy, cx = np.unravel_index(int(dist.argmax()), dist.shape)
    r = 85
    box = (cy - r, cy + r, cx - r, cx + r)
    print(f"placebo region centred ({cy},{cx}), {dist[cy, cx]:.0f} px from any subject")
    pl = {"PLACEBO-00-before": sel,
          "PLACEBO-01-after-F1d40": np.load(CACHE / "14-F1-mode-partition-d40.npy"),
          "PLACEBO-02-after-F2": np.load(CACHE / "13-F2.npy")}
    ref = None
    for tag, img in pl.items():
        crop = img[box[0]:box[1], box[2]:box[3]]
        png(crop, DEST / f"{tag}.png", lo, hi, scale=2)
        if ref is None:
            ref = crop
        else:
            d = np.abs(crop - ref)
            print(f"  {tag}: max |delta| = {d.max():.1f} DN, "
                  f"RMS = {np.sqrt((d ** 2).mean()):.3f} DN, "
                  f"changed px = {(d > 0).mean():.4f}")

    for f in DEST.iterdir():
        shutil.copy(f, OUT / f.name)
    print(f"\nwrote {len(list(DEST.iterdir()))} files to {DEST}")


if __name__ == "__main__":
    main()
