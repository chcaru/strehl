"""M115 s01 -- pick the ROIs, per stack, programmatically, flat FIRST (rule 9).

Three ROIs per stack:
  flat   -- lowest signal-gradient power that is still a real exposed surface.
            The null for the detail metric AND the external validation of the
            noise model (C5).
  detail -- highest signal-gradient power. Where the headroom is measured.
  edge   -- highest EDGE CONTRAST next to the flattest neighbourhood.  This is
            the ringing control's ROI: deconvolution overshoot shows up as
            structure on the flat side of a hard edge that is in no input frame.

Nothing is written under D:.
"""
import os, sys, json
import numpy as np
from scipy.ndimage import uniform_filter, sobel, maximum_filter, minimum_filter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m115lib as L

STACKS = {
    "109MSDCF": r"D:\personal\macro\109MSDCF",
    "119MSDCF": r"D:\personal\macro\119MSDCF",
}
B = 512
PAD = L.PAD


def main():
    res = {}
    for name, d in STACKS.items():
        files = L.stack_files(d)
        iso = L.iso_of(files[0])
        fn = L.fnumber_of(files[0])
        g, rn_e = L.noise_params(iso)
        mid = files[len(files) // 2]
        q = L.quad_green_full(mid)
        h, w = q.shape
        print(f"--- {name}: {len(files)} frames, ISO {iso}, marked f/{fn}, "
              f"g={g:.5f} DN/e-, RN={rn_e} e-, quad plane {w}x{h}")

        gx = sobel(q, axis=1)
        gy = sobel(q, axis=0)
        ten = uniform_filter(gx * gx + gy * gy, 65)
        m = uniform_filter(q, 65)
        nvar = L.quad_var(m, g, rn_e)
        ten_sig = np.maximum(ten - 24.0 * nvar, 0.0)

        marg = PAD + 8
        ys = np.arange(marg, h - marg - B, 64)
        xs = np.arange(marg, w - marg - B, 64)
        # score each candidate window by the MEAN signal-gradient power over the
        # WHOLE window, not its centre pixel.  Scoring the centre pixel picks a
        # window whose middle happens to be smooth and whose corners are not --
        # the first version of this script did that and V1 fired at 50x/160x.
        integ = np.cumsum(np.cumsum(ten_sig, 0), 1)

        def winmean(y, x, b):
            y0, x0, y1, x1 = y, x, y + b, x + b
            s = integ[y1 - 1, x1 - 1]
            if y0 > 0:
                s -= integ[y0 - 1, x1 - 1]
            if x0 > 0:
                s -= integ[y1 - 1, x0 - 1]
            if y0 > 0 and x0 > 0:
                s += integ[y0 - 1, x0 - 1]
            return s / (b * b)

        score = np.array([[winmean(y, x, B) for x in xs] for y in ys])
        lvl = np.array([[m[y + B // 2, x + B // 2] for x in xs] for y in ys])
        ok = (lvl > 200) & (lvl < 13000)

        sc = np.where(ok, score, -np.inf)
        iy, ix = np.unravel_index(np.argmax(sc), sc.shape)
        det = (int(xs[ix]), int(ys[iy]), B, B)

        # the flat ROI is searched at a SMALLER side and on a finer grid: a
        # genuinely featureless patch at 2:1 macro is small, and a 512-px
        # window is very unlikely to contain one.
        BF = 192
        ysf = np.arange(marg, h - marg - BF, 32)
        xsf = np.arange(marg, w - marg - BF, 32)
        scoref = np.array([[winmean(y, x, BF) for x in xsf] for y in ysf])
        lvlf = np.array([[winmean(y, x, BF) * 0 + m[y + BF // 2, x + BF // 2]
                          for x in xsf] for y in ysf])
        okf = (lvlf > 200) & (lvlf < 13000)
        sc2 = np.where(okf, scoref, np.inf)
        jy, jx = np.unravel_index(np.argmin(sc2), sc2.shape)
        flat = (int(xsf[jx]), int(ysf[jy]), BF, BF)

        # edge ROI: window whose local dynamic range is large but whose 25th
        # percentile of local gradient power is small -- a hard edge with genuine
        # flat ground beside it, which is what a ringing control needs.
        rng_ = maximum_filter(m, 33) - minimum_filter(m, 33)
        edge_sc = np.array([[float(rng_[y + B // 2, x + B // 2]) for x in xs] for y in ys])
        flatness = np.array([[float(np.percentile(
            ten_sig[y:y + B:8, x:x + B:8], 25)) for x in xs] for y in ys])
        combo = np.where(ok, edge_sc / (1.0 + flatness), -np.inf)
        ky, kx = np.unravel_index(np.argmax(combo), combo.shape)
        edge = (int(xs[kx]), int(ys[ky]), B, B)

        def roistat(roi):
            x, y, ww, hh = roi
            p = q[y:y + hh, x:x + ww]
            gxx = sobel(p, axis=1)
            gyy = sobel(p, axis=0)
            mm = float(p.mean())
            nv = float(L.quad_var(mm, g, rn_e))
            return dict(mean=mm, sd_s=float(p.std()), sigma_t=float(np.sqrt(nv)),
                        ten_sig=float((gxx * gxx + gyy * gyy).mean() - 24.0 * nv),
                        dyn=float(p.max() - p.min()))

        st = {k: roistat(v) for k, v in (("detail", det), ("flat", flat), ("edge", edge))}
        for k, roi in (("detail", det), ("flat", flat), ("edge", edge)):
            s = st[k]
            print(f"    {k:6s} ROI x={roi[0]:5d} y={roi[1]:5d} {roi[2]}x{roi[3]}: "
                  f"mean {s['mean']:7.0f} DN  sd_s {s['sd_s']:8.1f}  "
                  f"sigma_t {s['sigma_t']:6.2f}  ten_sig {s['ten_sig']:10.1f}  "
                  f"dyn {s['dyn']:7.0f}")
        r = st["flat"]["sd_s"] / st["flat"]["sigma_t"]
        print(f"    V1 check: flat sd_s / sigma_t = {r:.3f}   "
              f"({'VOID -- flat ROI carries structure' if r > 3 else 'ok'})")
        print(f"    rule 10: sd_s is SPATIAL, sigma_t is the MODEL temporal sigma; "
              f"they are reported side by side, never differenced")

        res[name] = dict(dir=d, n=len(files), iso=iso, fnumber=fn, g=g, rn_e=rn_e,
                         plane=[int(w), int(h)], detail_roi=det, flat_roi=flat,
                         edge_roi=edge, stats=st, v1_ratio=r)

    with open(os.path.join(L.OUT, "s01_rois.json"), "w") as fh:
        json.dump(res, fh, indent=2)
    print(f"\nwrote {os.path.join(L.OUT, 's01_rois.json')}")


if __name__ == "__main__":
    main()
