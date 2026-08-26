"""V-HULLCOST independent microcontrast instrument.

DEFINITION (mine, not BUILD-HULL's):
  microcontrast = RMS of the high-pass residual  H = I - Gauss(I, sigma)
  taken on the LINEAR camera-native 16-bit output, in DN (0..65535 scale).
  sigma = 1.0 output px  -> passes ~0.16 .. 0.5 cyc/px (top ~1.6 octaves, to Nyquist)
  sigma = 2.0 output px  -> passes ~0.08 .. 0.5 cyc/px
  retention% = 100 * hp_rms(clamped) / hp_rms(unclamped)

Also: radially-averaged power-spectral-density ratio clamped/unclamped at
stated normalised frequencies, which separates broadband (noise) loss from
band-limited (detail) loss.

Measured on the GREEN plane of the default binned camera-linear output:
G = 0.5*(G1+G2), white balance only, NO colour matrix, NO transfer curve, and
(unlike R and B) NO cosite resample. Both arms come from ONE binary.
"""
import sys, json
import numpy as np
import tifffile
from scipy.ndimage import gaussian_filter, uniform_filter

def load(path):
    a = tifffile.imread(path)
    assert a.dtype == np.uint16, "%s is %s, expected uint16" % (path, a.dtype)
    assert a.ndim == 3 and a.shape[2] == 3, "unexpected shape %r" % (a.shape,)
    return a

def hp_rms(x, sigma):
    return float(np.sqrt(np.mean((x - gaussian_filter(x, sigma, mode="reflect")) ** 2)))

def radial_psd(x, nbins=64):
    h, w = x.shape
    s = min(h, w, 2048)
    y0, x0 = (h - s) // 2, (w - s) // 2
    c = x[y0:y0 + s, x0:x0 + s].astype(np.float64)
    c = c - c.mean()
    win = np.hanning(s)
    c = c * win[:, None] * win[None, :]
    F = np.fft.rfft2(c)
    P = (F.real ** 2 + F.imag ** 2)
    fy = np.fft.fftfreq(s)[:, None]
    fx = np.fft.rfftfreq(s)[None, :]
    r = np.sqrt(fy ** 2 + fx ** 2)
    bins = np.linspace(0, 0.5, nbins + 1)
    idx = np.digitize(r.ravel(), bins) - 1
    ok = (idx >= 0) & (idx < nbins)
    tot = np.bincount(idx[ok], weights=P.ravel()[ok], minlength=nbins)
    cnt = np.bincount(idx[ok], minlength=nbins)
    with np.errstate(invalid="ignore", divide="ignore"):
        prof = tot / np.maximum(cnt, 1)
    centres = 0.5 * (bins[:-1] + bins[1:])
    return centres, prof

def main():
    ca, ua, tag = sys.argv[1], sys.argv[2], sys.argv[3]
    C, U = load(ca), load(ua)
    assert C.shape == U.shape, "shape mismatch %r vs %r" % (C.shape, U.shape)
    out = {"tag": tag, "shape": list(C.shape)}

    # --- exact-zero counts: survive any monotone curve -------------------
    for i, nm in enumerate("RGB"):
        out["zeros_%s_clamped" % nm] = int((C[:, :, i] == 0).sum())
        out["zeros_%s_unclamped" % nm] = int((U[:, :, i] == 0).sum())
    out["npix"] = int(C.shape[0] * C.shape[1])

    g_c = C[:, :, 1].astype(np.float32)
    g_u = U[:, :, 1].astype(np.float32)

    # --- raw difference ---------------------------------------------------
    d = g_u - g_c                      # unclamped minus clamped, DN
    out["G_mean_clamped_DN"] = float(g_c.mean())
    out["G_mean_unclamped_DN"] = float(g_u.mean())
    out["G_maxabs_diff_DN"] = float(np.abs(d).max())
    out["G_frac_diff_gt0"] = float((np.abs(d) > 0).mean())
    out["G_frac_diff_ge8DN"] = float((np.abs(d) >= 8).mean())
    out["G_rms_diff_DN"] = float(np.sqrt(np.mean(d.astype(np.float64) ** 2)))

    # --- microcontrast retention -----------------------------------------
    for sg in (1.0, 2.0):
        hc, hu = hp_rms(g_c, sg), hp_rms(g_u, sg)
        out["hp%.0f_clamped_DN" % sg] = hc
        out["hp%.0f_unclamped_DN" % sg] = hu
        out["retention_sigma%.0f_pct" % sg] = 100.0 * hc / hu if hu > 0 else float("nan")

    # --- spectral ratio ---------------------------------------------------
    f, pc = radial_psd(g_c)
    _, pu = radial_psd(g_u)
    ratio = np.sqrt(np.divide(pc, pu, out=np.ones_like(pc), where=pu > 0))  # amplitude ratio
    for q in (0.05, 0.10, 0.20, 0.30, 0.40, 0.45):
        j = int(np.argmin(np.abs(f - q)))
        out["ampratio_f%.2f" % q] = float(ratio[j])

    # --- SIGNAL vs NOISE --------------------------------------------------
    # Local structure S = |grad| of a *smoothed* image (sigma 2), which is
    # dominated by real subject edges rather than by per-pixel noise.
    sm = gaussian_filter(g_c, 2.0, mode="reflect")
    gy, gx = np.gradient(sm)
    S = np.sqrt(gy * gy + gx * gx)
    # Local flatness/darkness: read-noise regions are dark AND structureless.
    L = uniform_filter(g_c, 9, mode="reflect")
    ad = np.abs(d)
    hot = ad >= 8.0                       # where the clamp actually moved things
    out["hot_count"] = int(hot.sum())
    if hot.sum() > 0:
        out["hot_median_structure"] = float(np.median(S[hot]))
        out["hot_median_level_DN"] = float(np.median(L[hot]))
        # Percentile rank of hot pixels' structure/level within the whole frame
        out["hot_structure_pctile"] = float(
            (S < np.median(S[hot])).mean() * 100.0)
        out["hot_level_pctile"] = float((L < np.median(L[hot])).mean() * 100.0)
    out["frame_median_structure"] = float(np.median(S))
    out["frame_median_level_DN"] = float(np.median(L))
    # Correlation of |d| with structure over the whole frame
    a = ad.ravam if False else ad.ravel()
    b = S.ravel()
    out["corr_absdiff_structure"] = float(np.corrcoef(a, b)[0, 1])
    # Correlation of |d| with local level (darkness test)
    out["corr_absdiff_level"] = float(np.corrcoef(a, L.ravel())[0, 1])

    # --- where is the microcontrast loss largest? (for the crops) ---------
    # tile the frame, find the tile with the biggest hp-RMS drop
    T = 256
    best = None
    H, W = g_c.shape
    for y in range(0, H - T, T):
        for x in range(0, W - T, T):
            tc = g_c[y:y+T, x:x+T]; tu = g_u[y:y+T, x:x+T]
            ru = hp_rms(tu, 1.0)
            if ru < 1e-6: continue
            drop = ru - hp_rms(tc, 1.0)
            if best is None or drop > best[0]:
                best = (drop, y, x, ru)
    if best:
        out["worst_tile"] = {"drop_DN": float(best[0]), "y": best[1], "x": best[2],
                             "unclamped_hp_DN": float(best[3]),
                             "retention_pct": float(100.0*(best[3]-best[0])/best[3])}
    print(json.dumps(out, indent=1))

main()
