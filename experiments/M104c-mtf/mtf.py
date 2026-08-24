"""Slanted-edge MTF, ISO 12233 style. ASCII only (cp1252 hazard, rule 47 sibling)."""
import numpy as np, math
try:
    from scipy.special import erf as _erf
    def erf(x): return _erf(x)
except Exception:
    _v = np.vectorize(math.erf)
    def erf(x): return _v(x)

SUP = 4   # bins per pixel in the supersampled ESF

def mtf_from_roi(roi, sup=SUP):
    """roi: 2-D float, near-VERTICAL edge (dark|light). Returns dict."""
    roi = roi.astype(np.float64)
    h, w = roi.shape
    # 1. per-row edge location from the derivative centroid
    dx = np.diff(roi, axis=1)
    xs = np.arange(w - 1) + 0.5
    wts = np.abs(dx)
    denom = wts.sum(axis=1)
    good = denom > 0
    cen = np.full(h, np.nan)
    cen[good] = (wts[good] * xs).sum(axis=1) / denom[good]
    rows = np.arange(h)
    ok = np.isfinite(cen)
    # 2. fit the edge line, robustly (2 passes, drop >2 sigma)
    a, b = np.polyfit(rows[ok], cen[ok], 1)
    resid = cen[ok] - (a * rows[ok] + b)
    keep = np.abs(resid) < 2.0 * resid.std() if resid.std() > 0 else np.ones(ok.sum(), bool)
    a, b = np.polyfit(rows[ok][keep], cen[ok][keep], 1)
    angle_deg = math.degrees(math.atan(a))
    # 3. project every pixel onto the edge normal, bin to a supersampled ESF
    yy, xx = np.mgrid[0:h, 0:w]
    dist = (xx - (a * yy + b)) / math.sqrt(1.0 + a * a)
    lo, hi = dist.min(), dist.max()
    nb = int(math.floor((hi - lo) * sup))
    idx = np.clip(((dist - lo) * sup).astype(int), 0, nb - 1)
    s = np.bincount(idx.ravel(), weights=roi.ravel(), minlength=nb)
    n = np.bincount(idx.ravel(), minlength=nb)
    full = n > 0
    esf = np.full(nb, np.nan); esf[full] = s[full] / n[full]
    # keep the longest run of populated bins
    esf = esf[full]
    # 4. LSF = derivative, Hamming window
    lsf = np.diff(esf)
    m = len(lsf)
    lsf = lsf - np.median(np.concatenate([lsf[:m//8], lsf[-m//8:]]))
    win = np.hamming(m)
    # centre the window on the LSF centroid
    c = (np.arange(m) * np.abs(lsf)).sum() / np.abs(lsf).sum()
    shift = int(round(m / 2.0 - c))
    lsf = np.roll(lsf, shift)
    lsf = lsf * win
    # 5. FFT -> MTF
    F = np.abs(np.fft.rfft(lsf))
    F = F / F[0]
    freq = np.fft.rfftfreq(m, d=1.0 / sup)   # cycles per PIXEL
    # 6. MTF50 by linear interpolation on the first crossing
    below = np.where(F < 0.5)[0]
    mtf50 = float("nan")
    if len(below):
        i = below[0]
        if i > 0:
            f0, f1, y0, y1 = freq[i-1], freq[i], F[i-1], F[i]
            mtf50 = f0 + (0.5 - y0) * (f1 - f0) / (y1 - y0)
    mtf_nyq = float(np.interp(0.5, freq, F))
    return dict(angle=angle_deg, rows=int(ok.sum()), mtf50=mtf50, mtf_nyq=mtf_nyq,
                freq=freq, mtf=F, nbins=m)

def synth_edge(h, w, sigma, angle_deg=5.0, lo=0.2, hi=0.8, x0=None):
    """Exactly Gaussian-blurred edge, sampled point-wise. True MTF = exp(-2 pi^2 sigma^2 f^2)."""
    if x0 is None: x0 = w / 2.0
    a = math.tan(math.radians(angle_deg))
    yy, xx = np.mgrid[0:h, 0:w]
    dist = (xx - (a * yy + x0)) / math.sqrt(1 + a * a)
    return lo + (hi - lo) * 0.5 * (1.0 + erf(dist / (sigma * math.sqrt(2.0))))

if __name__ == "__main__":
    print("=== V1 ANALYTIC + V2 POSITIVE CONTROL ===")
    out = {}
    for sigma in (2.0, 3.0):
        img = synth_edge(256, 128, sigma)
        r = mtf_from_roi(img)
        truth = math.sqrt(math.log(2) / (2 * math.pi ** 2)) / sigma
        err = 100.0 * (r["mtf50"] - truth) / truth
        out[sigma] = r["mtf50"]
        print("sigma=%.1f  angle=%+.3f deg rows=%d  MTF50 measured=%.6f  analytic=%.6f  err=%+.2f%%  MTF@Nyq=%.4f"
              % (sigma, r["angle"], r["rows"], r["mtf50"], truth, err, r["mtf_nyq"]))
    ratio = out[3.0] / out[2.0]
    print("V2 ratio MTF50(3.0)/MTF50(2.0) = %.4f   predicted 0.6667   err=%+.2f%%"
          % (ratio, 100 * (ratio - 2.0/3.0) / (2.0/3.0)))
    print("")
    print("=== V3 NULL: two disjoint crops of the SAME image ===")
    big = synth_edge(512, 128, 2.0)
    ra = mtf_from_roi(big[0:200, :]); rb = mtf_from_roi(big[300:500, :])
    print("cropA MTF50=%.6f  cropB MTF50=%.6f  disagreement=%+.2f%%"
          % (ra["mtf50"], rb["mtf50"], 100 * (rb["mtf50"] - ra["mtf50"]) / ra["mtf50"]))
