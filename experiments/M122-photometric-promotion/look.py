"""M122 -- shared-stretch before/after sheets for the A0 / A1 arms.

Copied from experiments/ORCH-drift-check/photometric_look2.py (which is not mine
to edit) and repointed at C:\\dev\\strehl-out\\M122\\measure. The window
selection is byte-for-byte the same rule as blotch_ab.py: brightness bar then
smoothness, both computed on the SYMMETRIC MEAN of the two arms, so neither arm
picks the pixels it is judged on.

Both panels of a row share ONE stretch, taken from A0. Independent per-panel
stretching would make the comparison meaningless.

    python look.py <subject> [<subject> ...]

Reads C:\\dev\\strehl-out\\M122\\measure, writes C:\\dev\\strehl-out\\M122\\sheets.
Never touches D:\\.
"""

import os
import sys

import numpy as np
import tifffile
from PIL import Image

ROOT = r"C:\dev\strehl-out\M122\measure"
OUT = r"C:\dev\strehl-out\M122\sheets"
S, BORDER, STRIDE = 256, 400, 128
os.makedirs(OUT, exist_ok=True)


def load(p):
    a = tifffile.imread(p)
    assert a.dtype == np.uint16, "%s read as %s, expected uint16" % (p, a.dtype)
    return a[..., :3].astype(np.float64).mean(axis=2) if a.ndim == 3 else a.astype(np.float64)


def hf(w):
    lap = -4 * w[1:-1, 1:-1] + w[:-2, 1:-1] + w[2:, 1:-1] + w[1:-1, :-2] + w[1:-1, 2:]
    return float(np.sqrt((lap ** 2).mean()))


def sheet(subj):
    A0 = load(os.path.join(ROOT, "%s__A0.tif" % subj))
    A1 = load(os.path.join(ROOT, "%s__A1.tif" % subj))
    assert A0.shape == A1.shape
    M = (A0 + A1) * 0.5
    H, W = A0.shape

    allw = []
    for y in range(BORDER, H - S - BORDER, STRIDE):
        for x in range(BORDER, W - S - BORDER, STRIDE):
            w = M[y:y + S, x:x + S]
            allw.append((float(w.mean()), float(w[::8, ::8].std()), x, y))
    bar = float(np.percentile([a[0] for a in allw], 80))
    pool = sorted([a for a in allw if a[0] >= bar], key=lambda t: t[1])

    # Render ALL 12 windows the A/B scored, in the A/B's own order, plus the most
    # textured window. Showing only the top 3 would be a selection; showing the
    # scored set is not, because the rule is the same one blotch_ab.py used and it
    # never looks at the outcome.
    picks = [("smooth%02d" % i, pool[i][2], pool[i][3]) for i in range(12)]
    tex = sorted(allw, key=lambda t: -t[1])[0]
    picks.append(("TEXTURED", tex[2], tex[3]))

    print("%s: %d windows scanned, brightness bar %.0f" % (subj, len(allw), bar))
    rows = []
    for tag, x, y in picks:
        w0, w1 = A0[y:y + S, x:x + S], A1[y:y + S, x:x + S]
        lo, hi = np.percentile(w0, [0.5, 99.5])
        span = max(hi - lo, 1e-9)
        panels = []
        for lum in (w0, w1):
            st = np.clip((lum - lo) / span, 0, 1) * 255.0
            panels.append(np.repeat(np.repeat(st.astype(np.uint8), 2, 0), 2, 1))
        gap = np.full((panels[0].shape[0], 12), 255, np.uint8)
        rows.append(np.concatenate([panels[0], gap, panels[1]], axis=1))
        print("  %-9s x=%-5d y=%-5d hf %9.1f -> %9.1f  ratio %.4f   lvl %.5f"
              % (tag, x, y, hf(w0), hf(w1), hf(w1) / hf(w0), w1.mean() / w0.mean()))

    vgap = np.full((12, rows[0].shape[1]), 255, np.uint8)
    out = rows[0]
    for r in rows[1:]:
        out = np.concatenate([out, vgap, r], axis=0)
    out = np.array(Image.fromarray(out).resize(
        (out.shape[1] // 2, out.shape[0] // 2), Image.LANCZOS))
    p = os.path.join(OUT, "M122-SHEET-%s.png" % subj)
    Image.fromarray(out).save(p)
    print("  wrote %s  (left A0 default, right A1 --photometric, ONE shared stretch per row;"
          " rows: the 12 scored smooth windows, then the most textured)\n" % p)


if __name__ == "__main__":
    for s in sys.argv[1:]:
        sheet(s)
