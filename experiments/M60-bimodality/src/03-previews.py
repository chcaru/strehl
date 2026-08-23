"""M60 step 3 — high-resolution previews for HAND labelling, and a scene-identity check.

Renders 2x-binned green previews of several frames so occluding boundaries can be
marked by eye. The labels must not come from the focus volume (AGENTS rule 17).
"""

import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m60lib as L  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.abspath(os.path.join(HERE, "..", "fig"))
DATA = os.path.abspath(os.path.join(HERE, "..", "data"))


def render(g, out, lo=None, hi=None):
    from PIL import Image
    v = (g - (lo if lo is not None else np.percentile(g, 0.5)))
    v = v / max(1e-6, ((hi if hi is not None else np.percentile(g, 99.8)) - (lo if lo is not None else np.percentile(g, 0.5))))
    v = np.clip(v, 0, 1) ** (1 / 2.2)
    Image.fromarray((v * 255).astype(np.uint8)).save(out)


def bin2(g, b):
    h = (g.shape[0] // b) * b
    w = (g.shape[1] // b) * b
    return g[:h, :w].reshape(h // b, b, w // b, b).mean((1, 3))


if __name__ == "__main__":
    # 1. scene-identity check across the three bee stacks (fact 50's trap: the same
    #    subject shot twice is one sample, not two).
    print("=== scene identity, normalised cross-correlation of 8x-binned frame 0 ===")
    ref = {}
    for s in ("bee-1", "bee-2", "bee-3", "wrapped-text-1", "wrapped-text-2"):
        g = bin2(L.load_green(L.frames(s)[len(L.frames(s)) // 2]), 8)
        ref[s] = (g - g.mean()) / (g.std() + 1e-9)
    names = list(ref)
    print("%-16s" % "", "".join("%-16s" % n for n in names))
    for a in names:
        row = []
        for b in names:
            row.append("%-16.4f" % float((ref[a] * ref[b]).mean()))
        print("%-16s" % a, "".join(row))

    # 2. high-resolution previews for labelling
    for s in ("bee-3", "bee-1", "wrapped-text-1"):
        fs = L.frames(s)
        n = len(fs)
        for k in [int(round(f * (n - 1))) for f in (0.15, 0.35, 0.5, 0.65, 0.85)]:
            g = bin2(L.load_green(fs[k]), 2)
            out = os.path.join(FIG, "03-%s-k%03d.png" % (s, k))
            render(g, out, lo=0.0, hi=float(np.percentile(g, 99.7)))
            print("wrote", out, g.shape)
