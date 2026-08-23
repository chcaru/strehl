"""M60 — contact sheets: every cell at four FIXED frame indices.

The indices are chosen by position in the stack (0.15, 0.38, 0.62, 0.85 of n),
never by any focus measure, so nothing here can leak the quantity under test
into the labels. Purpose: see whether each cell's background actually carries
texture, since the through-focus mean image is too blurred to tell.
"""

import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m60lib as L  # noqa: E402
from cells import CELLS  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.abspath(os.path.join(HERE, "..", "fig"))
DATA = os.path.abspath(os.path.join(HERE, "..", "data"))
FRACS = (0.15, 0.38, 0.62, 0.85)


if __name__ == "__main__":
    from PIL import Image
    by_stack = {}
    for c in CELLS:
        by_stack.setdefault(c[0], []).append(c)

    rows = []
    for stack, cs in by_stack.items():
        fs = L.frames(stack)
        n = len(fs)
        idx = [int(round(f * (n - 1))) for f in FRACS]
        planes = [L.load_green(fs[i]).astype(np.float32) for i in idx]
        for stack_, name, cls, y0, y1, x0, x1 in cs:
            tiles, sds = [], []
            for P in planes:
                a = P[y0:y1, x0:x1]
                sds.append(float(np.std(L.sobel_mag(a))))
                hi = float(np.percentile(a, 99.5))
                v = np.clip(a / max(hi, 1e-6), 0, 1) ** (1 / 2.2)
                tiles.append((v * 255).astype(np.uint8))
            h, w = tiles[0].shape
            sheet = np.zeros((h, w * 4 + 24, ), np.uint8) + 255
            for j, t in enumerate(tiles):
                sheet[:, j * (w + 8):j * (w + 8) + w] = t
            sc = max(1, int(round(max(h, w * 4) / 900)))
            im = Image.fromarray(sheet)
            im = im.resize((sheet.shape[1] // sc, sheet.shape[0] // sc))
            im.save(os.path.join(FIG, "08-sheet-%s-%s.png" % (cls, name)))
            rows.append((stack, name, cls, idx, sds))
            print("%-16s %-18s %-8s k=%s  sobel-sd=%s"
                  % (stack, name, cls, idx, " ".join("%7.1f" % s for s in sds)))
    with open(os.path.join(DATA, "08-sheets.txt"), "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write("%s %s %s k=%s sobel_sd=%s\n"
                     % (r[0], r[1], r[2], r[3], ["%.1f" % s for s in r[4]]))
