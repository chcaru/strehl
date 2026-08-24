"""K16 - amplify the residual: is the l3-cr difference a FRINGE (ringing) or a
sharpness difference? At 1.67/255 the ESF says any fringe is near the visual
threshold, so amplify it 24x and look at its SPATIAL STRUCTURE. Ringing has a
signed lobe that hugs the edge and reverses across it; a sharpness difference is
a single-signed ridge centred ON the edge."""
import os
import numpy as np
from PIL import Image
from scipy import ndimage
import tifffile
from k12_neff_ringing import luma

R = r"C:\dev\strehl-out\M113\render3"
V = r"C:\dev\strehl-out\M113\view3"
nn, cr, l3 = (luma(os.path.join(R, f"lin-{k}.tif")) for k in ("nn", "cr", "l3"))
S, AMP = 120, 24.0
for n, (x0, y0) in enumerate([(2691, 254), (2713, 458)]):
    a, b, c = (v[y0:y0+S, x0:x0+S] for v in (nn, cr, l3))
    vmin, vmax = float(a.min()), float(a.max())
    rngv = max(vmax - vmin, 1e-9)
    base = np.power(np.clip((a - vmin)/rngv, 0, 1), 1/2.2)
    tiles = [(base*255).astype(np.uint8)]
    for nm, d in (("l3-cr", c-b), ("l3-nn", c-a), ("cr-nn", b-a)):
        q = np.clip(0.5 + AMP*d/rngv, 0, 1)
        tiles.append((q*255).astype(np.uint8))
        inside = np.abs(d)/rngv
        print(f"ROI{n} {nm:6s}: mean |diff| {100*inside.mean():.3f}% of ROI range, "
              f"p99.9 {100*np.percentile(inside,99.9):.3f}%, "
              f"= {255*np.percentile(inside,99.9):.2f}/255 levels")
    strip = np.concatenate([np.pad(t, ((0,0),(0,4)), constant_values=255) for t in tiles], axis=1)
    p = os.path.join(V, f"resid-roi{n}.png")
    Image.fromarray(strip).resize((strip.shape[1]*4, strip.shape[0]*4), Image.NEAREST).save(p)
    print(f"  wrote {p}  (nearest | l3-cr | l3-nn | cr-nn, all amplified {AMP:.0f}x about mid-grey)")