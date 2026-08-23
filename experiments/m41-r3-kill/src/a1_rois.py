"""M41 step 1 -- pick the detail ROI and the flat ROI, per stack, programmatically.

Rule 9: the flat-ROI control is chosen and run FIRST, not as a closing check.
Rule 7: statistics are taken from raw_image_visible only (the active area),
never from the padded decode buffer.
Rule 23: every gradient is taken on a 2-D plane that has already been extracted;
no 3-D cube is ever handed to scipy.ndimage.sobel.

Nothing is written to C:\\dev\\macro or D:\\ -- rawpy.imread opens read-only.
"""
import os, sys, glob, json
import numpy as np
import rawpy, exifread
from scipy.ndimage import uniform_filter, sobel

BLACK = 512
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")
os.makedirs(OUT, exist_ok=True)

STACKS = {
    "109MSDCF": r"C:\dev\macro\test\109MSDCF",
    "119MSDCF": r"C:\dev\macro\test\119MSDCF",
    "coffee-bubbles": r"D:\personal\macro\coffee-bubbles",
}


def iso_of(path):
    with open(path, "rb") as fh:
        t = exifread.process_file(fh, details=False)
    for k in ("EXIF ISOSpeedRatings", "Image ISOSpeedRatings"):
        if k in t:
            return int(str(t[k]).split(",")[0].strip("[] "))
    return None


def quad_green(path):
    """G = (G1+G2)/2 on the active area only, black-subtracted. Matches the
    shipped binned output's green channel definition."""
    with rawpy.imread(path) as r:
        v = r.raw_image_visible
        g1 = v[0::2, 1::2].astype(np.float32)
        g2 = v[1::2, 0::2].astype(np.float32)
    return 0.5 * (g1 + g2) - BLACK


def main():
    res = {}
    for name, d in STACKS.items():
        files = sorted(glob.glob(os.path.join(d, "*.ARW")))
        if not files:
            print(f"{name}: NO ARW FILES at {d}")
            continue
        iso = iso_of(files[0])
        g = iso / 436.8
        rn_e = 1.47 if iso >= 400 else 4.20
        mid = files[len(files) // 2]
        q = quad_green(mid)
        h, w = q.shape
        # per-quad-pixel temporal variance model, halved because G=(G1+G2)/2
        # of two independent CFA sites: var_q = 0.5*(g*S + (RN*g)^2)
        print(f"--- {name}: {len(files)} frames, ISO {iso}, g={g:.5f} DN/e-, "
              f"RN={rn_e} e-, quad plane {w}x{h}")

        gx = sobel(q, axis=1)
        gy = sobel(q, axis=0)
        ten = uniform_filter(gx * gx + gy * gy, 65)
        m = uniform_filter(q, 65)
        nvar = 0.5 * (g * np.maximum(m, 0.0) + (rn_e * g) ** 2)
        ten_sig = ten - 24.0 * nvar          # E[gx^2+gy^2] = 24 sigma^2 for 3x3 Sobel

        B = 512                              # ROI side, quad px
        pad = 64
        sub = ten_sig[pad:h - pad - B, pad:w - pad - B]
        subm = m[pad:h - pad - B, pad:w - pad - B]
        # coarse grid search so we do not pick overlapping/edge windows
        ys = np.arange(0, sub.shape[0], 128)
        xs = np.arange(0, sub.shape[1], 128)
        score = np.array([[ten_sig[pad + y + B // 2, pad + x + B // 2] for x in xs] for y in ys])
        lvl = np.array([[m[pad + y + B // 2, pad + x + B // 2] for x in xs] for y in ys])
        # detail ROI: highest signal-gradient power, well exposed
        ok = (lvl > 200) & (lvl < 13000)
        sc = np.where(ok, score, -np.inf)
        iy, ix = np.unravel_index(np.argmax(sc), sc.shape)
        det = (int(pad + xs[ix]), int(pad + ys[iy]), B, B)
        # flat ROI: lowest signal-gradient power, still above the noise floor so
        # it is a real surface and not a clipped black region
        sc2 = np.where(ok, score, np.inf)
        jy, jx = np.unravel_index(np.argmin(sc2), sc2.shape)
        flat = (int(pad + xs[jx]), int(pad + ys[jy]), B, B)

        def roistat(roi):
            x, y, ww, hh = roi
            p = q[y:y + hh, x:x + ww]
            gxx = sobel(p, axis=1); gyy = sobel(p, axis=0)
            mm = float(p.mean())
            nv = 0.5 * (g * max(mm, 0.0) + (rn_e * g) ** 2)
            return dict(mean=mm, sd=float(p.std()),
                        model_sigma=float(np.sqrt(nv)),
                        ten_sig=float((gxx * gxx + gyy * gyy).mean() - 24.0 * nv))

        ds, fs = roistat(det), roistat(flat)
        print(f"    detail ROI x={det[0]} y={det[1]} {B}x{B}: mean {ds['mean']:.0f} DN, "
              f"sd {ds['sd']:.1f}, model sigma {ds['model_sigma']:.2f}, ten_sig {ds['ten_sig']:.1f}")
        print(f"    flat   ROI x={flat[0]} y={flat[1]} {B}x{B}: mean {fs['mean']:.0f} DN, "
              f"sd {fs['sd']:.1f}, model sigma {fs['model_sigma']:.2f}, ten_sig {fs['ten_sig']:.1f}")
        print(f"    flat-ROI sd/model_sigma = {fs['sd'] / fs['model_sigma']:.3f}  "
              f"(rule 10: >>1 means the ROI carries structure, not just noise)")
        res[name] = dict(dir=d, n=len(files), iso=iso, g=g, rn_e=rn_e,
                         plane=[int(w), int(h)], detail_roi=det, flat_roi=flat,
                         detail=ds, flat=fs)
    with open(os.path.join(OUT, "rois.json"), "w") as fh:
        json.dump(res, fh, indent=2)
    print(f"\nwrote {os.path.join(OUT, 'rois.json')}")


if __name__ == "__main__":
    main()
