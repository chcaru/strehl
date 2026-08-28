"""V-MOTE P4 -- LOOK AT THE PIXELS.  1:1 crops, no resampling anywhere.

Every crop below is a straight integer slice.  Nothing is resized; the only
transforms are (a) a stated linear stretch to 8 bit and (b) for the "detrended"
flats, division by a quadratic fitted OUTSIDE the mote, which is the same
background model vm_depth.py measures with.  The stretch window is printed for
every file so a reader can undo it.
"""
import os, sys
import numpy as np
import tifffile
from PIL import Image

CACHE = r"C:\dev\strehl-out\V-MOTE\cache"
DST   = r"C:\dev\strehl-out\V-MOTE\crops"
MAST  = r"C:\dev\strehl-out\ORCH-FAITHFUL\faithful"
QH, QW = 2344, 3520
SITE_Q = (3434, 2305)            # BUILD-DEFECT, quads
SITE_P = (6868, 4610)            # = 2 * SITE_Q, photosites
SITE_M = (7008, 4450)            # V-EYES / DELIVER-V5, master pixels
CTRL_Q = (3100, 2305)            # clean control, SAME distance from bottom edge


def save(a, path, lo, hi, note):
    b = np.clip((a - lo) / (hi - lo), 0, 1)
    Image.fromarray((b * 255 + 0.5).astype(np.uint8)).save(path)
    print("  %-46s %-28s stretch [%.5g, %.5g]" % (os.path.basename(path), note, lo, hi))


def quad_crop(f, cx, cy, half):
    return f[cy - half:cy + half, cx - half:cx + half]


def detrend(f, cx, cy, half, r_in=90, r_out=140):
    y0, y1, x0, x1 = cy - half, cy + half, cx - half, cx + half
    R = max(half, r_out)
    yy0, yy1 = max(0, cy - R), min(QH, cy + R + 1)
    xx0, xx1 = max(0, cx - R), min(QW, cx + R + 1)
    sub = f[yy0:yy1, xx0:xx1]
    dy = (np.arange(yy0, yy1) - cy)[:, None] * np.ones((1, xx1 - xx0))
    dx = np.ones((yy1 - yy0, 1)) * (np.arange(xx0, xx1) - cx)[None, :]
    r = np.hypot(dx, dy)
    m = (r >= r_in) & (r <= r_out)
    A = np.stack([np.ones(m.sum()), dx[m], dy[m], dx[m]**2, dx[m]*dy[m], dy[m]**2], 1)
    c, *_ = np.linalg.lstsq(A, sub[m], rcond=None)
    bg = c[0] + c[1]*dx + c[2]*dy + c[3]*dx**2 + c[4]*dx*dy + c[5]*dy**2
    res = sub / bg - 1.0
    return res[cy - yy0 - half:cy - yy0 + half, cx - xx0 - half:cx - xx0 + half]


def upsample2(a):
    return np.repeat(np.repeat(a, 2, 0), 2, 1)


def main():
    os.makedirs(DST, exist_ok=True)
    f = np.load(os.path.join(CACHE, "flat_all.npy")).astype(np.float64)
    print("== flats, quad grid %dx%d ==" % (QW, QH))
    H = 100                                  # 200x200 quads = 400x400 photosites
    for tag, (cx, cy) in (("mote2", SITE_Q), ("control", CTRL_Q)):
        raw = quad_crop(f, cx, cy, H)
        save(upsample2(raw), os.path.join(DST, "01-flat-%s-1to1-linear.png" % tag),
             float(raw.min()), float(raw.max()),
             "flat %s, 400x400 photosites" % tag)
        det = detrend(f, cx, cy, H)
        save(upsample2(det), os.path.join(DST, "02-flat-%s-detrended-pm5pct.png" % tag),
             -0.05, 0.05, "flat %s, detrended" % tag)
        print("      %s: detrended core r<=8q mean %+0.3f%%  crop min %+0.2f%% max %+0.2f%%"
              % (tag, 100 * det[H-8:H+9, H-8:H+9].mean(), 100 * det.min(), 100 * det.max()))

    print("\n== delivered masters, C:\\dev\\strehl-out\\ORCH-FAITHFUL\\faithful ==")
    subs = ["highly-angled-ruler-mm-cpl", "pencil-flatter-angle-cpl",
            "flower-bud-alone-cpl", "109MSDCF", "bee-3-cpl", "coffee-bean"]
    CW = 400
    for s in subs:
        a = tifffile.imread(os.path.join(MAST, s + ".tiff"))
        h, w = a.shape[:2]
        x0, y0 = w - CW, h - CW
        crop = a[y0:y0 + CW, x0:x0 + CW, :]
        g = crop[..., 1].astype(np.float64)
        lo, hi = np.percentile(g, 0.5), np.percentile(g, 99.5)
        rgb = np.clip((crop.astype(np.float64) - lo) / max(hi - lo, 1), 0, 1)
        Image.fromarray((rgb * 255 + 0.5).astype(np.uint8)).save(
            os.path.join(DST, "10-master-%s-corner400.png" % s))
        print("  10-master-%-36s corner slice x0=%d y0=%d %dx%d  "
              "V-EYES site at (%d,%d) in crop, BUILD-DEFECT site at (%d,%d)  "
              "stretch [%.0f,%.0f] DN16"
              % (s + "-corner400.png", x0, y0, CW, CW,
                 SITE_M[0] - x0, SITE_M[1] - y0, SITE_P[0] - x0, SITE_P[1] - y0, lo, hi))
        del a
    return 0


if __name__ == "__main__":
    sys.exit(main())
