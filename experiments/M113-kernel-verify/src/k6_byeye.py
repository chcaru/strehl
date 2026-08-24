"""M113: the by-eye A/B. REUSES experiments/ORCH-drift-check/kernel_crops.py --
same REGIONS, same SCALE, same nearest-neighbour magnification, same no-post
rule -- with OUT and ARMS repointed at my three arms so that lanczos3, which
ORCH never rendered, is in the comparison.

Then a tighter 1:1 zoom on a single hair cluster, small enough to actually look
at, because a 3752x1970 contact sheet is not something anyone inspects honestly.
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = r"C:\dev\blog\death-of-software\projects\strehl"
sys.path.insert(0, os.path.join(ROOT, "experiments", "ORCH-drift-check"))
import kernel_crops as KC  # noqa: E402

KC.OUT = r"C:\dev\strehl-out\M113\view"
KC.ARMS = ["catmull-rom", "lanczos3", "nearest"]
KC.main()

print("\n--- tight 1:1 zooms for actual inspection ---")
imgs = {a: KC.load(a) for a in KC.ARMS}
ZOOMS = [("thorax hairs", 900, 3300, 300, 220),
         ("hair tips against background", 1000, 3240, 300, 220),
         ("leg + claw", 1560, 3820, 300, 220)]
S = 3
for zname, x, y, rw, rh in ZOOMS:
    W = 6 + len(KC.ARMS) * (rw * S + 6)
    H = 28 + rh * S + 6
    c = Image.new("RGB", (W, H), (18, 18, 20))
    d = ImageDraw.Draw(c)
    xc = 6
    for arm in KC.ARMS:
        t = Image.fromarray(KC.to8(imgs[arm][y:y + rh, x:x + rw])).resize(
            (rw * S, rh * S), Image.NEAREST)
        c.paste(t, (xc, 28))
        d.text((xc, 8), f"{arm}", fill=(245, 220, 120))
        xc += rw * S + 6
    p = os.path.join(KC.OUT, f"ZOOM-{zname.replace(' ', '-').replace('+','')}.png")
    c.save(p)
    print("wrote", p, c.size)
