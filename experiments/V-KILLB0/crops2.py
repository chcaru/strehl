"""V-KILLB0 matched crops.

Coherence cannot separate "noise removed" from "signal attenuated" when the two
arms share source frames (their noise is correlated), so the verdict on the
disputed subjects has to be made on pixels.  This emits A and B at 1:1 with an
IDENTICAL stretch taken from arm A, so any difference in the image is a
difference in the data and not in the display.  Numbers required by the house
rule (median, clip%, black%) are printed for the crop itself, not the frame.

Site choice is stated explicitly rather than hunted: "struct" takes the 512-box
with the greatest mid-frequency structure energy in arm A, which is where a
softening would be most visible; "flat" takes the least, which is where a grain
win would be most visible.  Both are chosen from arm A ONLY, so the choice
cannot favour either arm.
"""
import os
import sys

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, uniform_filter

import bandprobe as bp

OUT = r"C:\dev\strehl-out\V-KILLB0\crops"


def site(la, mode, box=512):
    s = np.abs(gaussian_filter(la, 1.5) - gaussian_filter(la, 4.0))
    m = uniform_filter(s, box)
    h, w = la.shape
    b = box // 2 + 8
    m[:b, :] = m[-b:, :] = m[:, :b] = m[:, -b:] = (0 if mode == "struct" else 1e18)
    idx = int(np.argmax(m)) if mode == "struct" else int(np.argmin(m))
    cy, cx = divmod(idx, w)
    return cy - box // 2, cx - box // 2


def main():
    A, B, label, mode = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    zoom = int(sys.argv[5]) if len(sys.argv) > 5 else 2
    ia, ib = bp.load(A), bp.load(B)
    la = bp.channels(ia)["L"]
    y, x = site(la, mode)
    box = 512
    ca = ia[y:y + box, x:x + box]
    cb = ib[y:y + box, x:x + box]
    ga = la[y:y + box, x:x + box]
    gb = bp.channels(ib)["L"][y:y + box, x:x + box]

    lo, hi = np.percentile(ca, 0.5), np.percentile(ca, 99.5)
    if hi <= lo:
        hi = lo + 1

    def to8(c):
        return np.clip((c.astype(np.float64) - lo) / (hi - lo), 0, 1) ** (1 / 1.0) * 255

    pa, pb = to8(ca).astype(np.uint8), to8(cb).astype(np.uint8)
    gap = np.full((box, 8, 3), 255, np.uint8)
    im = Image.fromarray(np.concatenate([pa, gap, pb], axis=1))
    im = im.resize((im.width * zoom, im.height * zoom), Image.NEAREST)
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, f"{label}-{mode}.png")
    im.save(p)

    fa = ga - gaussian_filter(ga, 0.6366)
    fb = gb - gaussian_filter(gb, 0.6366)
    ra, rb = np.sqrt((fa ** 2).mean()), np.sqrt((fb ** 2).mean())
    print(f"== CROP {label} {mode} at y={y} x={x} box={box} zoom={zoom}  -> {p}")
    print(f"   stretch (shared, from A): lo={lo:.0f} hi={hi:.0f}")
    for nm, c in (("A(default)", ga), ("B(b0x4)", gb)):
        print(f"   {nm:<11} median={np.median(c):8.0f} mean={c.mean():8.1f} "
              f"clip%={100*(c>=65000).mean():6.3f} black%={100*(c<=200).mean():6.3f} "
              f"p1={np.percentile(c,1):.0f} p99={np.percentile(c,99):.0f}")
    print(f"   fine 0.25-0.50 rms: A={ra:.1f} B={rb:.1f} ratio={rb/ra:.4f}")
    print(f"   crop mean shift: {100*(gb.mean()/ga.mean()-1):+.3f}%")


if __name__ == "__main__":
    main()
