"""For each flagged subject: WHERE is the elevation, and is it visible there?

Cuts a 1:1 crop straddling the silhouette so the flagged band and background
both appear in one frame, and prints the band profile beside it. Fixed gamma,
no autoscale -- the tone difference IS the measurement.

Controls included: two subjects the instrument calls clean. A crop of a flagged
subject means nothing unless a clean one, cut the same way, looks different.
"""
import os, sys
import numpy as np
import tifffile
from PIL import Image, ImageDraw
from scipy.ndimage import distance_transform_edt, label

sys.path.insert(0, r"C:\dev\blog\death-of-software\projects\strehl\experiments\ORCH-drift-check")
import halo_profile as H

FAITH = r"C:\dev\strehl-out\ORCH-FAITHFUL\faithful"
OUTD = r"D:\strehl-out\V-REVIEW\halo\crops"
SIZE = 620
GAMMA = 2.2
SUBS = [("flat-on-ruler-cpl", "HALO +5680"), ("tweezers-cpl", "HALO bump 1567"),
        ("lavendar-cpl", "HALO +351"), ("119MSDCF", "HALO +820"),
        ("bee-1-cpl", "clean -3441"), ("leaf-2-cpl", "clean -1809")]


def band_report(y, sub=4):
    ys = y[::sub, ::sub]
    t, subj = H.segment(ys)
    lab, n = label(subj)
    dom = int(np.argmax(np.bincount(lab.ravel())[1:])) + 1
    d, ind = distance_transform_edt(~subj, return_indices=True)
    d = d * sub
    own = (lab[ind[0], ind[1]] == dom) & (~subj)
    far = (d >= H.FAR[0]) & (d < H.FAR[1])
    fl = float(np.median(ys[far]))
    out = []
    for lo, hi in H.NEAR:
        m = own & (d >= lo) & (d < hi)
        if int(m.sum()) > H.MIN_BANDPX:
            out.append((lo, hi, float(np.median(ys[m])) - fl, int(m.sum())))
    return out, fl, subj, d


for stem, tag in SUBS:
    f = os.path.join(FAITH, stem + ".tiff")
    img = tifffile.imread(f)
    yf = H.luma(img)
    bands, fl, subj4, d4 = band_report(yf)
    peak = max(bands, key=lambda b: b[2]) if bands else None
    print("\n=== %-26s %s   farfield %.0f ===" % (stem, tag, fl))
    for lo, hi, v, n in bands:
        mark = "  <== max" if peak and (lo, hi) == (peak[0], peak[1]) else ""
        print("   d %3d-%3d : %+9.1f DN   (%d px)%s" % (lo, hi, v, n, mark))

    # site: box centred on the silhouette edge, wide enough to hold the peak band
    subjf = np.repeat(np.repeat(subj4, 4, 0), 4, 1)[:yf.shape[0], :yf.shape[1]]
    best, bxy = -1, None
    for yy in range(0, img.shape[0] - SIZE, 220):
        for xx in range(0, img.shape[1] - SIZE, 220):
            s = subjf[yy:yy + SIZE, xx:xx + SIZE].mean()
            if 0.30 < s < 0.70:
                g = float(np.abs(np.gradient(yf[yy:yy + SIZE:8, xx:xx + SIZE:8])[0]).mean())
                if g > best:
                    best, bxy = g, (yy, xx)
    if bxy is None:
        print("   (no boundary box found)")
        continue
    y0, x0 = bxy
    c = img[y0:y0 + SIZE, x0:x0 + SIZE, :3].astype(np.float32) / 65535.0
    p = (np.clip(c, 0, 1) ** (1 / GAMMA) * 255).astype(np.uint8)
    sheet = Image.new("RGB", (SIZE, SIZE + 30), (16, 16, 16))
    sheet.paste(Image.fromarray(p), (0, 30))
    dr = ImageDraw.Draw(sheet)
    lbl = "%s  %s  peak band d=%d-%d %+.0f DN" % (
        stem, tag, peak[0], peak[1], peak[2]) if peak else stem
    dr.text((6, 9), lbl, fill=(255, 255, 0))
    o = os.path.join(OUTD, "LOOK-%s.jpg" % stem)
    sheet.save(o, quality=95)
    print("   crop (y=%d,x=%d) -> %s" % (y0, x0, o))
