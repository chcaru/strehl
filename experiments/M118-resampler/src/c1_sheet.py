"""M118 arm 3 -- the images. Full renders, 1:1 crops, and one contact sheet per subject.

The owner looks at these before reading a word of prose, so the controls that
make them honest are stated here and enforced in code:

  * EXPOSURE IS PINNED. Every arm is rendered at the single `--exposure=N` that
    the BASELINE arm's --auto-exposure chose (see r1_render.py). If each arm
    re-chose its own gain the sheet would compare exposures, not kernels.
  * CROP SITES ARE CHOSEN ON THE BASELINE. catmull-rom is the incumbent, so
    picking the sites on it cannot flatter the candidate.
  * THE SITES ARE IDENTICAL ACROSS ARMS, to the pixel, by construction -- one
    site list, applied to every arm's file.
  * The 1:1 panels are cut at 100% with NO resampling of any kind. The x3 panels
    use NEAREST-neighbour magnification only, which adds no interpolation of mine
    on top of the interpolation under test.
"""
import json
import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image, ImageDraw

OUT = Path(r"C:\dev\strehl-out\M118")
HERE = Path(__file__).parent.parent
ARMS = ["nearest", "bilinear", "catmull-rom", "lanczos2", "lanczos3"]
BASELINE = "catmull-rom"

CROP = 360        # px, at 1:1 on the full-resolution sRGB grid
N_SITES = 3
ZOOM = 3


def to8(a: np.ndarray) -> np.ndarray:
    return (np.clip(a.astype(np.float32) / 65535.0, 0, 1) * 255 + 0.5).astype(np.uint8)


def pick_sites(view: np.ndarray) -> list:
    """Top-gradient, well-separated sites on the BASELINE arm, inside the central region."""
    g = view[:, :, 1].astype(np.float32)
    h, w = g.shape
    # coarse gradient on a 1/8 decimation, purely to choose where to look
    d = g[::8, ::8]
    gy = np.zeros_like(d); gx = np.zeros_like(d)
    gy[1:-1, :] = d[2:, :] - d[:-2, :]
    gx[:, 1:-1] = d[:, 2:] - d[:, :-2]
    energy = np.hypot(gy, gx)
    # block-sum over CROP-sized blocks
    b = CROP // 8
    hh, ww = energy.shape[0] // b, energy.shape[1] // b
    blocks = energy[:hh * b, :ww * b].reshape(hh, b, ww, b).sum(axis=(1, 3))
    # restrict to the central region: the merge's border is uncovered/rescaled
    m = np.zeros_like(blocks, dtype=bool)
    m[hh // 5: hh - hh // 5, ww // 5: ww - ww // 5] = True
    blocks = np.where(m, blocks, -np.inf)
    sites = []
    for _ in range(N_SITES):
        iy, ix = np.unravel_index(np.argmax(blocks), blocks.shape)
        y, x = iy * CROP, ix * CROP
        if y + CROP > h or x + CROP > w:
            blocks[iy, ix] = -np.inf
            continue
        sites.append((int(y), int(x)))
        blocks[max(0, iy - 1):iy + 2, max(0, ix - 1):ix + 2] = -np.inf
    return sites


def label(img: Image.Image, text: str, h: int = 22) -> Image.Image:
    out = Image.new("RGB", (img.width, img.height + h), (16, 16, 16))
    out.paste(img, (0, h))
    ImageDraw.Draw(out).text((5, 5), text, fill=(235, 235, 235))
    return out


def build(subject: str) -> dict:
    rec = json.loads((HERE / "out" / f"r1_{subject}.json").read_text())
    sdir = OUT / subject
    print(f"\n=== {subject}: images (exposure pinned at {rec.get('pinned_exposure')})")

    base_view = tifffile.imread(str(rec["arms"][BASELINE]["view"]))
    sites = pick_sites(base_view)
    print(f"  crop sites chosen on the {BASELINE} baseline: {sites}")
    del base_view

    panels = {}
    for arm in ARMS:
        v = tifffile.imread(str(rec["arms"][arm]["view"]))
        rgb = to8(v)
        Image.fromarray(rgb).save(sdir / f"{subject}__{arm}__full.png")
        for i, (y, x) in enumerate(sites):
            c = rgb[y:y + CROP, x:x + CROP]
            im = Image.fromarray(c)
            im.save(sdir / f"{subject}__{arm}__crop{i+1}.png")
            im.resize((CROP * ZOOM, CROP * ZOOM), Image.NEAREST).save(
                sdir / f"{subject}__{arm}__crop{i+1}x{ZOOM}.png")
            panels[(arm, i)] = im
        del v, rgb
        print(f"  {arm:<12} full + {len(sites)} crops")

    # contact sheet: one row per site, one column per arm, 1:1
    pad = 6
    cw, ch = CROP + pad, CROP + 22 + pad
    sheet = Image.new("RGB", (cw * len(ARMS) + pad, ch * len(sites) + pad + 26), (16, 16, 16))
    for r, (y, x) in enumerate(sites):
        for c, arm in enumerate(ARMS):
            tag = f"{arm}" + ("  [DEFAULT]" if arm == BASELINE else "")
            sheet.paste(label(panels[(arm, r)], f"{tag}   site{r+1} @ ({x},{y}) 1:1"),
                        (pad + c * cw, pad + r * ch))
    ImageDraw.Draw(sheet).text(
        (pad, ch * len(sites) + pad + 4),
        f"{subject}  limit={rec['limit']}  gate={rec['gate']}  exposure={rec.get('pinned_exposure')} "
        f"(PINNED across arms)  --srgb  M118 @ 4beac73  1:1, no resampling",
        fill=(200, 200, 200))
    sp = OUT / f"SHEET-{subject}-100.png"
    sheet.save(sp)

    zsheet = Image.new("RGB", (cw * len(ARMS) + pad, ch * len(sites) + pad + 26), (16, 16, 16))
    zc = CROP // ZOOM
    for r, (y, x) in enumerate(sites):
        for c, arm in enumerate(ARMS):
            sub = panels[(arm, r)].crop((0, 0, zc, zc)).resize((CROP, CROP), Image.NEAREST)
            tag = f"{arm}" + ("  [DEFAULT]" if arm == BASELINE else "")
            zsheet.paste(label(sub, f"{tag}   site{r+1} x{ZOOM} NEAREST"),
                         (pad + c * cw, pad + r * ch))
    ImageDraw.Draw(zsheet).text(
        (pad, ch * len(sites) + pad + 4),
        f"{subject}  x{ZOOM} nearest-neighbour magnification of the top-left quarter of each 1:1 crop",
        fill=(200, 200, 200))
    zp = OUT / f"SHEET-{subject}-{ZOOM}00.png"
    zsheet.save(zp)
    print(f"  sheets: {sp}\n          {zp}")
    return {"subject": subject, "sites": sites, "sheet_100": str(sp), "sheet_zoom": str(zp)}


if __name__ == "__main__":
    res = [build(s) for s in (sys.argv[1:] or ["flat-on-ruler-cpl", "wrapped-text-1", "bee-3-cpl"])]
    (HERE / "out" / "c1_sheets.json").write_text(json.dumps(res, indent=2))
