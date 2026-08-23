"""M60 step 5 — draw a coordinate grid over a frame so cells can be placed by eye.

Green-sublattice coordinates (2344 rows x 3514 cols). Labels every 200 px.
"""

import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m60lib as L  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.abspath(os.path.join(HERE, "..", "fig"))


def gridded(stack, k, out, binf=2, step=200):
    from PIL import Image, ImageDraw
    g = L.load_green(L.frames(stack)[k])
    h = (g.shape[0] // binf) * binf
    w = (g.shape[1] // binf) * binf
    g = g[:h, :w].reshape(h // binf, binf, w // binf, binf).mean((1, 3))
    hi = float(np.percentile(g, 99.7))
    v = np.clip(g / max(hi, 1e-6), 0, 1) ** (1 / 2.2)
    im = Image.fromarray((v * 255).astype(np.uint8)).convert("RGB")
    d = ImageDraw.Draw(im)
    for x in range(0, 3514, step):
        d.line([(x / binf, 0), (x / binf, im.height)], fill=(255, 60, 60), width=1)
        d.text((x / binf + 2, 2), str(x), fill=(255, 60, 60))
    for y in range(0, 2344, step):
        d.line([(0, y / binf), (im.width, y / binf)], fill=(60, 160, 255), width=1)
        d.text((2, y / binf + 2), str(y), fill=(60, 160, 255))
    im.save(out)
    return im.size


if __name__ == "__main__":
    for stack, ks in (("bee-3", (104, 194, 253)), ("bee-1", (104, 194)),
                      ("wrapped-text-1", (64,))):
        for k in ks:
            out = os.path.join(FIG, "05-grid-%s-k%03d.png" % (stack, k))
            print("wrote", out, gridded(stack, k, out))
