"""Crop 109MSDCF where magenta is DENSEST, so the defect can be seen, not inferred.

The histogram says 84.21% of this master's saturated pixels render magenta and
11.76% of the whole frame does. That is a number. This turns it into a picture,
at true 1:1 (CROP=380, inside the viewer's resolving limit), because a defect
nobody has looked at is a defect nobody has confirmed.
"""
import os
import sys

import numpy as np
import tifffile
from PIL import Image

CROP = 380
MAG_DN = 1200.0


def main():
    src = None
    for cand in sorted(os.listdir(r"C:\dev\strehl-out\acceptance\SHIP-V4")):
        if cand.startswith("109MSDCF") and cand.endswith(".tiff"):
            src = os.path.join(r"C:\dev\strehl-out\acceptance\SHIP-V4", cand)
    a = tifffile.imread(src)
    r = a[..., 0].astype(np.float32)
    g = a[..., 1].astype(np.float32)
    b = a[..., 2].astype(np.float32)
    m = ((r - g > MAG_DN) & (b - g > MAG_DN)).astype(np.float32)

    s = 64
    hh, ww = m.shape[0] // s, m.shape[1] // s
    blk = m[:hh * s, :ww * s].reshape(hh, s, ww, s).mean(axis=(1, 3))
    pad = CROP // s + 1
    blk[:pad, :] = 0
    blk[-pad:, :] = 0
    blk[:, :pad] = 0
    blk[:, -pad:] = 0
    i = int(np.argmax(blk))
    cx, cy = (i % ww) * s + s // 2, (i // ww) * s + s // 2
    x0 = max(0, min(a.shape[1] - CROP, cx - CROP // 2))
    y0 = max(0, min(a.shape[0] - CROP, cy - CROP // 2))
    c = a[y0:y0 + CROP, x0:x0 + CROP]
    dens = float(m[y0:y0 + CROP, x0:x0 + CROP].mean())

    out = r"C:\dev\strehl-out\ORCH-TRUE11\109MSDCF_magenta_%d_%d.png" % (x0, y0)
    Image.fromarray(((c.astype(np.uint32) + 128) >> 8).astype(np.uint8)).save(out)
    print("densest magenta block at (%d,%d); crop %dx%d at (%d,%d)"
          % (cx, cy, CROP, CROP, x0, y0))
    print("magenta density inside this crop: %.2f%%" % (dens * 100))
    print("wrote %s" % out)

    # what do the three channels actually do at those pixels?
    sel = (m[y0:y0 + CROP, x0:x0 + CROP] > 0)
    if sel.any():
        rr = c[..., 0].astype(np.float32)[sel]
        gg = c[..., 1].astype(np.float32)[sel]
        bb = c[..., 2].astype(np.float32)[sel]
        print("\nat the magenta pixels, channel medians (16-bit DN, ceiling 65535):")
        print("   R %8.0f   G %8.0f   B %8.0f" % (np.median(rr), np.median(gg), np.median(bb)))
        print("   R at ceiling: %5.1f%%   G at ceiling: %5.1f%%   B at ceiling: %5.1f%%"
              % ((rr >= 65535).mean() * 100, (gg >= 65535).mean() * 100,
                 (bb >= 65535).mean() * 100))
        print("\nIf R and B sit at the ceiling while G does NOT, the highlight is")
        print("being clipped per-channel after white balance: the two channels WB")
        print("multiplies UP saturate first, G is left behind, and the result is")
        print("R+B without G, which is magenta.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
