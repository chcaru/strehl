"""Picture the election-indeterminacy mechanism.

Three panels at the same location, for a cluster where an isolated pixel elects
a frame far from its neighbours:

  election map (gate 4)   which frame won, false-coloured -- the speckle
  M0, gate 0              pure selection: the speckle made visible as patchwork
  A0, gate 4 (shipped)    the same region after the gate averages ~46 frames

Named ELECTION-OUTLIER, not MOTION-ARTEFACT. ORCH asked for the latter name,
but motion_hunt.py's own rigid-subject control refuted the motion reading
(tweezers-cpl cannot move and reads 2.076%), and election_indeterminacy.py
found the mechanism to be a flat-region argmax instead. Labelling these frames
as motion would be asserting a cause the evidence does not support.
"""

import json
import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image, ImageDraw
from scipy import ndimage

ROOT = Path(r"C:\dev\strehl-out\M116")
VIEW, MAPS, OUT = ROOT / "view", ROOT / "maps", ROOT / "images"
HALF = 160          # plane px each side of the cluster
BAR = 34


def u8(a):
    return (a >> 8).astype(np.uint8) if a.dtype == np.uint16 else a.astype(np.uint8)


def panel(img, title, sub):
    o = Image.new("RGB", (img.width, img.height + BAR), (16, 16, 16))
    o.paste(img, (0, BAR))
    d = ImageDraw.Draw(o)
    d.text((6, 4), title, fill=(255, 255, 255))
    d.text((6, 18), sub, fill=(170, 170, 170))
    return o


def main() -> int:
    hunt = json.loads((ROOT / "motion-hunt.json").read_text())
    ind = json.loads((ROOT / "election-indeterminacy.json").read_text())
    OUT.mkdir(exist_ok=True)

    for s in ("bee-3-cpl", "tweezers-cpl"):
        idx = tifffile.imread(MAPS / f"{s}__A0-index.tif").astype(np.float32)
        if idx.ndim == 3:
            idx = idx[..., 0]
        nfr = max(idx.max(), 1)

        views = {}
        for arm in ("M0", "A0"):
            p = VIEW / f"{s}__{arm}.tif"
            if p.exists():
                views[arm] = Image.fromarray(u8(tifffile.imread(p)))
        if not views:
            print(f"{s}: no viewing renders; re-render before running this")
            continue

        r = ind[s]
        for n, c in enumerate(hunt[s]["clusters"][:3], 1):
            x, y, jump = c["x"], c["y"], c["jump"]
            x0, y0 = max(0, x - HALF), max(0, y - HALF)
            x1, y1 = x0 + 2 * HALF, y0 + 2 * HALF

            sl = idx[y0:y1, x0:x1]
            rgb = (np.stack([sl / nfr, 1 - sl / nfr,
                             np.abs(0.5 - sl / nfr) * 2], -1) * 255)
            em = Image.fromarray(rgb.astype(np.uint8)).resize(
                (2 * HALF * 2, 2 * HALF * 2), Image.NEAREST)

            ps = [panel(em, "election map (which frame won)",
                        f"isolated cluster jumps {jump:.0f} frames, "
                        f"{c['px']} px")]
            for arm, lab in (("M0", "M0 gate 0 = pure selection"),
                             ("A0", "A0 gate 4 = shipped default")):
                if arm not in views:
                    continue
                im = views[arm].crop((2 * x0, 2 * y0, 2 * x1, 2 * y1))
                ps.append(panel(im, lab,
                                f"outliers in flattest 20%: "
                                f"{100 * r['frac_in_flattest_quintile']:.1f}% "
                                f"(chance 20.0%)"))

            w = sum(p.width for p in ps) + 8 * (len(ps) + 1)
            h = max(p.height for p in ps) + 40
            sheet = Image.new("RGB", (w, h), (28, 28, 28))
            xx = 8
            for p in ps:
                sheet.paste(p, (xx, 32))
                xx += p.width + 8
            ImageDraw.Draw(sheet).text(
                (8, 10),
                f"M116  {s}  ELECTION OUTLIER {n} at plane ({x},{y})  "
                f"commit 4beac73  -- an argmax with nothing to choose between, "
                f"NOT motion (rigid tweezers reads 2.076%)",
                fill=(255, 255, 255))
            f = OUT / f"{s}__ELECTION-OUTLIER__{n}.png"
            sheet.save(f)
            print(f"  wrote {f.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
