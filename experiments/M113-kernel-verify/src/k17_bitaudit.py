"""M113 k17: re-run the BY-EYE kernel comparison in true 16-bit.

ORCH's fleet notice: PIL.Image.open() silently returns uint8 for 16-bit RGB
TIFFs. My quantitative kernel work all read through tifffile and is unaffected,
but k6_byeye.py line 24 calls KC.load() from ORCH's kernel_crops.py, which uses
Image.open(). Confirmed live on my own render: PIL gives uint8 max=159 where
tifffile gives uint16 max=40781.

Those crops fed two visual judgements: fact 1374 (nearest resolves thorax hairs
that catmull-rom merges) and my attack surface 4 (does lanczos3 ring visibly on
hair silhouettes). Ringing is a SMALL-SIGNAL question near edges, which is
exactly the case ORCH flags as most suspect, so I re-measure rather than argue.

The test does both paths on the same pixels: read once with tifffile (truth) and
once through the uint8 downconversion PIL would have applied, and ask whether any
RANKING or any VISIBLE feature changes. A conclusion that survives both is safe;
one that flips was decided by the reader.
"""
import os
import numpy as np
import tifffile
from PIL import Image

R = r"C:\dev\strehl-out\M113\render3"
V = r"C:\dev\strehl-out\M113\view-k17"
os.makedirs(V, exist_ok=True)
ARMS = ("nn", "cr", "l3")

def luma16(p):
    a = tifffile.imread(p).astype(np.float64)
    return 0.2126 * a[:, :, 0] + 0.7152 * a[:, :, 1] + 0.0722 * a[:, :, 2]

def as_pil_would(y):
    """The uint8 array PIL hands you, promoted back to the 16-bit scale."""
    return np.floor(y / 256.0).clip(0, 255) * 256.0

def modulation(y):
    """Peak-to-trough hair modulation: robust spread of the high-pass."""
    from scipy import ndimage
    hp = y - ndimage.uniform_filter(y, 9)
    return float(np.percentile(hp, 99.5) - np.percentile(hp, 0.5))

def undershoot(y):
    """Ringing proxy: how far the darkest pixels dip below the local dark floor."""
    from scipy import ndimage
    lo = ndimage.minimum_filter(ndimage.uniform_filter(y, 15), 25)
    d = lo - y
    return float(np.percentile(d[d > 0], 99.9)) if (d > 0).any() else 0.0

lum = {k: luma16(os.path.join(R, "lin-%s.tif" % k)) for k in ARMS}
H, W = lum["nn"].shape
print("binned luma %dx%d ; range nn %.0f..%.0f" % (W, H, lum["nn"].min(), lum["nn"].max()))

ROIS = [("thorax hairs", 450, 1650, 300, 220),
        ("hair tips vs background", 500, 1620, 300, 220),
        ("leg + claw", 780, 1910, 300, 220)]
ROIS = [(n, x, y, w, h) for (n, x, y, w, h) in ROIS if y + h <= H and x + w <= W]

print("\n%-26s %-6s %12s %12s %9s   %12s %12s %9s"
      % ("roi", "arm", "mod16", "mod8", "d%", "ring16", "ring8", "d%"))
flips = []
for (name, x, y, w, h) in ROIS:
    m16, m8, r16, r8 = {}, {}, {}, {}
    for k in ARMS:
        t = lum[k][y:y + h, x:x + w]
        p8 = as_pil_would(t)
        m16[k], m8[k] = modulation(t), modulation(p8)
        r16[k], r8[k] = undershoot(t), undershoot(p8)
        print("%-26s %-6s %12.1f %12.1f %+8.1f%%   %12.1f %12.1f %+8.1f%%"
              % (name if k == "nn" else "", k, m16[k], m8[k],
                 100 * (m8[k] / m16[k] - 1) if m16[k] else 0,
                 r16[k], r8[k], 100 * (r8[k] / r16[k] - 1) if r16[k] else 0))
    o16 = sorted(ARMS, key=lambda k: -m16[k]); o8 = sorted(ARMS, key=lambda k: -m8[k])
    ro16 = sorted(ARMS, key=lambda k: -r16[k]); ro8 = sorted(ARMS, key=lambda k: -r8[k])
    print("     modulation ranking  16-bit %s | 8-bit %s   %s"
          % (">".join(o16), ">".join(o8), "SAME" if o16 == o8 else "*** FLIPPED ***"))
    print("     ringing    ranking  16-bit %s | 8-bit %s   %s"
          % (">".join(ro16), ">".join(ro8), "SAME" if ro16 == ro8 else "*** FLIPPED ***"))
    if o16 != o8 or ro16 != ro8:
        flips.append(name)

    tiles = []
    for k in ARMS:
        t = lum[k][y:y + h, x:x + w]
        q = ((t - t.min()) / max(t.max() - t.min(), 1e-9) * 255).astype(np.uint8)
        tiles.append(np.pad(q, ((0, 0), (0, 4)), constant_values=255))
    strip = np.concatenate(tiles, axis=1)
    fp = os.path.join(V, "K17-%s.png" % name.replace(" ", "-").replace("+", ""))
    Image.fromarray(strip).resize((strip.shape[1] * 3, strip.shape[0] * 3),
                                  Image.NEAREST).save(fp)
    print("     wrote %s  (nearest | catmull-rom | lanczos3, 3x, from TRUE 16-bit)" % fp)

print("\n" + "=" * 96)
print("VERDICT: %s" % ("no ranking changed between the 16-bit and 8-bit readers -- the by-eye "
                       "conclusions are reader-independent"
                       if not flips else "RANKINGS FLIPPED in: %s" % ", ".join(flips)))
print("=" * 96)