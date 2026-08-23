"""M41 step 1b -- REPLACES a1_rois.py, which was WRONG.

What was wrong with a1_rois.py (rule 15: new name, new script, say what broke):
it scored each candidate 512x512 window by the value of the noise-corrected
Tenengrad field at the window's CENTRE PIXEL, not by the window's mean.  A
single pixel is not a window statistic, so the "flat" ROI it returned carried
50x-148x the modelled photon-transfer sigma -- i.e. it was not flat at all, and
rule 10's own detector says so.  a1_rois.py's output is not used anywhere.

This version block-reduces properly: the score for a window is the MEAN of the
noise-corrected Tenengrad field over that whole window, obtained with a
uniform_filter of the window's own side length.
"""
import os, glob, json
import numpy as np
import rawpy, exifread
from scipy.ndimage import uniform_filter, sobel

BLACK = 512
B = 512
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")
os.makedirs(OUT, exist_ok=True)
STACKS = {
    "109MSDCF": r"C:\dev\macro\test\109MSDCF",
    "119MSDCF": r"C:\dev\macro\test\119MSDCF",
    "coffee-bubbles": r"D:\personal\macro\coffee-bubbles",
}


def iso_of(p):
    with open(p, "rb") as fh:
        t = exifread.process_file(fh, details=False)
    for k in ("EXIF ISOSpeedRatings", "Image ISOSpeedRatings"):
        if k in t:
            return int(str(t[k]).split(",")[0].strip("[] "))
    return None


def quad_green(path):
    with rawpy.imread(path) as r:
        v = r.raw_image_visible
        g1 = v[0::2, 1::2].astype(np.float32)
        g2 = v[1::2, 0::2].astype(np.float32)
    return 0.5 * (g1 + g2) - BLACK


def main():
    res = {}
    for name, d in STACKS.items():
        files = sorted(glob.glob(os.path.join(d, "*.ARW")))
        iso = iso_of(files[0]); g = iso / 436.8
        rn_e = 1.47 if iso >= 400 else 4.20
        # the flat/detail choice must not be made on one frame's focus state, so
        # score on the MAXIMUM over frames of the noise-corrected Tenengrad:
        # a region that is flat in every frame is genuinely featureless.
        acc_max = None
        acc_mean = None
        for f in files[::max(1, len(files) // 6)]:
            q = quad_green(f)
            gx = sobel(q, axis=1); gy = sobel(q, axis=0)
            e = gx * gx + gy * gy
            m = uniform_filter(q, B)
            eB = uniform_filter(e, B)
            nvar = 0.5 * (g * np.maximum(m, 0.0) + (rn_e * g) ** 2)
            t = eB - 24.0 * nvar
            acc_max = t if acc_max is None else np.maximum(acc_max, t)
            acc_mean = m if acc_mean is None else acc_mean
        h, w = acc_max.shape
        half = B // 2
        valid = np.zeros_like(acc_max, bool)
        valid[half:h - half, half:w - half] = True
        lvl_ok = (acc_mean > 120) & (acc_mean < 13000)
        sc = np.where(valid & lvl_ok, acc_max, -np.inf)
        iy, ix = np.unravel_index(np.argmax(sc), sc.shape)
        det = (int(ix - half), int(iy - half), B, B)
        sc2 = np.where(valid & lvl_ok, acc_max, np.inf)
        jy, jx = np.unravel_index(np.argmin(sc2), sc2.shape)
        flat = (int(jx - half), int(jy - half), B, B)

        qm = quad_green(files[len(files) // 2])

        def stat(roi):
            x, y, ww, hh = roi
            p = qm[y:y + hh, x:x + ww]
            mm = float(p.mean())
            nv = 0.5 * (g * max(mm, 0.0) + (rn_e * g) ** 2)
            hp = p - uniform_filter(p, 9)
            return dict(mean=mm, sd=float(p.std()), hp_sd=float(hp.std()),
                        model_sigma=float(np.sqrt(nv)))

        ds, fs = stat(det), stat(flat)
        print(f"--- {name}: {len(files)} frames ISO {iso} g={g:.5f} plane {w}x{h}")
        print(f"    detail x={det[0]} y={det[1]}: mean {ds['mean']:.0f} sd {ds['sd']:.1f} "
              f"hp_sd {ds['hp_sd']:.2f} model_sigma {ds['model_sigma']:.2f} "
              f"hp_sd/sigma {ds['hp_sd']/ds['model_sigma']:.2f}")
        print(f"    flat   x={flat[0]} y={flat[1]}: mean {fs['mean']:.0f} sd {fs['sd']:.1f} "
              f"hp_sd {fs['hp_sd']:.2f} model_sigma {fs['model_sigma']:.2f} "
              f"hp_sd/sigma {fs['hp_sd']/fs['model_sigma']:.2f}   <-- rule 10 detector; "
              f"near 1.0 means the ROI is noise-dominated, which is what a flat ROI must be")
        res[name] = dict(dir=d, n=len(files), iso=iso, g=g, rn_e=rn_e,
                         plane=[int(w), int(h)], detail_roi=det, flat_roi=flat,
                         detail=ds, flat=fs)
    with open(os.path.join(OUT, "rois_b.json"), "w") as fh:
        json.dump(res, fh, indent=2)
    print("wrote out/rois_b.json")


if __name__ == "__main__":
    main()
