"""V-bestframe: a per-tile "never worse than the best single frame" instrument.

Independent of strehl/blend-render: the frame side is decoded with rawpy, the
merge side is read with tifffile. No code is shared with the thing under audit.

GEOMETRY. blend-render shrinks the field of view so every frame covers every
output pixel (log line "coverage: field of view scaled to S"), then writes at
full pixel count, so the merge is MAGNIFIED by 1/S relative to a frame. Worse,
S is not one number: focus breathing makes magnification a function of frame
index (measured on flowers-cpl: s = 0.990 at k=0, 0.935 at k=88 -- linear).
Model:  merge(Q) shows the scene at  frame(s_k * Q + t_k).

NEITHER SIDE IS EVER RESAMPLED FOR MEASUREMENT. Resampling destroys exactly the
high-frequency content under test. Instead the band radii on the frame side are
multiplied by s_k, so both sides probe the same PHYSICAL scale on their own grid.

TONE. The two pipelines apply different curves. A monotone transfer T is fitted
per frame from registered, heavily blurred samples and applied to the frame,
putting both arms in the merge's photometric space.

NOISE. A single frame is far noisier than a 176-frame merge, and raw band energy
would hand every flat tile to the frame on noise alone. Per image, a noise floor
sigma(level) is fitted as the lower envelope of per-tile band RMS against tile
mean level (shot noise is level-dependent, so one global floor is wrong) and
subtracted in POWER. Raw and corrected are both reported.
"""
import numpy as np, rawpy, tifffile
from scipy import ndimage

# --- pre-registered before any subject was measured -------------------------
FINE = (1.0, 2.0)      # primary band: DoG, structures ~3-8 px in the merge grid
MID  = (2.5, 5.0)      # secondary band: ~8-20 px, far less noise-prone
NTX, NTY = 22, 16      # uniform grid over the WHOLE frame; no feature selection
REG_BAND = (4.0, 16.0) # at down=8 this is 32-128 px physical: survives heavy defocus
REG_DOWN = 8
REG_COARSE = np.arange(0.82, 1.0601, 0.01)
REG_FINE_STEP = 0.0025
REG_SCALES = np.arange(0.82, 1.0601, 0.0025)
PEAK_OK = 0.45         # below this a direct fit is not trusted; the model is used
LUMA = np.array([0.2126, 0.7152, 0.0722], np.float32)


def luma(rgb):
    return (rgb.reshape(-1, 3).astype(np.float32) @ LUMA).reshape(rgb.shape[:2])


def boxdown(a, f):
    h, w = a.shape[0] // f * f, a.shape[1] // f * f
    return a[:h, :w].reshape(h // f, f, w // f, f).mean(axis=(1, 3))


def dog(a, s1, s2, truncate=3.0):
    return (ndimage.gaussian_filter(a, s1, mode="nearest", truncate=truncate) -
            ndimage.gaussian_filter(a, s2, mode="nearest", truncate=truncate))


def _prep(a):
    a = a - a.mean(); n = np.linalg.norm(a)
    return a / n if n > 0 else a


def decode(path):
    with rawpy.imread(str(path)) as r:
        a = r.postprocess(output_bps=16, no_auto_bright=True, use_camera_wb=True)
    assert a.dtype == np.uint16, f"rawpy returned {a.dtype}, NOT uint16"
    return a


def raw_green_half(path):
    """Half-res green from the Bayer mosaic, no demosaic. ~5x cheaper than a full
    postprocess, and structure is all registration needs."""
    with rawpy.imread(str(path)) as r:
        pat = r.raw_pattern
        gy, gx = [(i // 2, i % 2) for i in range(4) if pat[i // 2, i % 2] == 1][0]
        g = r.raw_image_visible[gy::2, gx::2].astype(np.float32)
        blk = float(np.mean(r.black_level_per_channel))
    return np.sqrt(np.maximum(g - blk, 0.0))     # sqrt: measured to beat linear and log


def read_merge(path):
    a = tifffile.imread(str(path))
    assert a.dtype == np.uint16, f"merge {path} is {a.dtype}, NOT uint16"
    return a


def register2(merge_reg, frame_reg, band=REG_BAND, down=REG_DOWN):
    """Coarse-to-fine scale search: 25 coarse steps then 9 fine, instead of 97.
    Measured 25x faster than the flat sweep with the same answer."""
    s0, t0, p0 = register(merge_reg, frame_reg, REG_COARSE, band, down)
    fine = np.arange(s0 - 0.01, s0 + 0.01001, REG_FINE_STEP)
    s1, t1, p1 = register(merge_reg, frame_reg, fine, band, down)
    return (s1, t1, p1) if p1 >= p0 else (s0, t0, p0)


def register(merge_reg, frame_reg, scales=REG_SCALES, band=REG_BAND, down=REG_DOWN):
    """merge_reg and frame_reg are both at 1/down of their own full-res grid.
    Returns (s, (tx, ty) in full-res px, peak)."""
    A = _prep(dog(merge_reg, *band)); FA = np.fft.rfft2(A); H, W = merge_reg.shape
    best = (-1.0, None, None)
    for s in scales:
        Z = ndimage.zoom(frame_reg, 1.0 / s, order=1)
        if Z.shape[0] < H or Z.shape[1] < W:
            continue
        oy, ox = (Z.shape[0] - H) // 2, (Z.shape[1] - W) // 2
        C = _prep(dog(Z[oy:oy + H, ox:ox + W], *band))
        R = np.fft.irfft2(FA * np.conj(np.fft.rfft2(C)), A.shape)
        k = int(np.argmax(R)); peak = float(R.flat[k])
        if peak > best[0]:
            uy, ux = np.unravel_index(k, R.shape)
            uy = uy - H if uy > H // 2 else uy
            ux = ux - W if ux > W // 2 else ux
            best = (peak, s, (down * s * (ux + ox), down * s * (uy + oy)))
    return best[1], best[2], best[0]


def robust_line(k, y, w, iters=4, nsig=3.0):
    """Weighted least squares with iterative outlier rejection. Focus breathing
    and stage drift are smooth in k, so a frame too defocused to register can
    still be placed by the frames that could."""
    k = np.asarray(k, float); y = np.asarray(y, float); w = np.asarray(w, float).copy()
    keep = w > 0
    for _ in range(iters):
        if keep.sum() < 3:
            break
        c = np.polyfit(k[keep], y[keep], 1, w=w[keep])
        r = y - np.polyval(c, k)
        s = 1.4826 * np.median(np.abs(r[keep] - np.median(r[keep]))) + 1e-12
        nk = keep & (np.abs(r - np.median(r[keep])) < nsig * s)
        if nk.sum() == keep.sum():
            keep = nk; break
        keep = nk
    if keep.sum() < 3:
        return np.polyfit(k, y, 1), np.ones_like(k, bool)
    return np.polyfit(k[keep], y[keep], 1, w=w[keep]), keep


def fit_tone(merge8, frame8, s, t, nbin=48):
    """Monotone transfer frame-level -> merge-level from registered blurred pairs."""
    Hm, Wm = merge8.shape
    yy, xx = np.mgrid[0:Hm, 0:Wm].astype(np.float32)
    fy = (s * (yy * 8.0) + t[1]) / 8.0
    fx = (s * (xx * 8.0) + t[0]) / 8.0
    ok = (fy >= 0) & (fy <= frame8.shape[0] - 1) & (fx >= 0) & (fx <= frame8.shape[1] - 1)
    src = ndimage.map_coordinates(frame8, [fy.ravel(), fx.ravel()], order=1,
                                  mode="nearest").reshape(Hm, Wm)
    m, f = merge8[ok], src[ok]
    edges = np.unique(np.quantile(f, np.linspace(0, 1, nbin + 1)))
    idx = np.clip(np.digitize(f, edges[1:-1]), 0, max(len(edges) - 2, 0))
    xs, ys = [], []
    for b in range(len(edges) - 1):
        sel = idx == b
        if sel.sum() >= 200:
            xs.append(np.median(f[sel])); ys.append(np.median(m[sel]))
    if len(xs) < 2:
        return np.array([0.0, 1.0]), np.array([0.0, 1.0]), float(ok.mean())
    return np.asarray(xs), np.maximum.accumulate(np.asarray(ys)), float(ok.mean())


def apply_tone(a, xs, ys):
    """np.interp clamps at the ends, which would flatten highlights and hide the
    detail under test. Extrapolate linearly from the end segments instead."""
    out = np.interp(a, xs, ys)
    gl = (ys[1] - ys[0]) / max(xs[1] - xs[0], 1e-6)
    gh = (ys[-1] - ys[-2]) / max(xs[-1] - xs[-2], 1e-6)
    lo, hi = a < xs[0], a > xs[-1]
    out[lo] = ys[0] + gl * (a[lo] - xs[0])
    out[hi] = ys[-1] + gh * (a[hi] - xs[-1])
    return out


def tone_lut(xs, ys):
    """np.interp over 33M px costs 4.2 s; a 65536-entry LUT gather costs 0.7 s.
    It quantises the frame luma to integer DN (<0.29 DN RMS), which slightly
    INFLATES the frame band and so biases toward finding a merge deficit --
    the conservative direction for an H1 verdict."""
    return apply_tone(np.arange(65536, dtype=np.float64), xs, ys).astype(np.float32)


def apply_tone_fast(a, lut):
    return lut[np.clip(a, 0, 65535).astype(np.uint16)]


def tile_edges(n, npart):
    return np.linspace(0, n, npart + 1).round().astype(int)


def _tile_reduce(img, f2, m2, ye, xe):
    out = np.empty((len(ye) - 1, len(xe) - 1, 3), np.float64)
    for i in range(len(ye) - 1):
        for j in range(len(xe) - 1):
            sl = (slice(ye[i], ye[i + 1]), slice(xe[j], xe[j + 1]))
            out[i, j, 0] = img[sl].mean()
            out[i, j, 1] = np.sqrt(f2[sl].mean())
            out[i, j, 2] = np.sqrt(m2[sl].mean())
    return out


def tile_stats(img, ye, xe):
    f2 = dog(img, *FINE).astype(np.float64) ** 2
    m2 = dog(img, *MID).astype(np.float64) ** 2
    return _tile_reduce(img, f2, m2, ye, xe)


def frame_tile_stats(img, s, t, ye_m, xe_m):
    """Tiles are defined in MERGE coords and measured on the frame's OWN grid at
    the mapped location, with band radii scaled by s so the physical scale matches."""
    f2 = dog(img, FINE[0] * s, FINE[1] * s).astype(np.float64) ** 2
    m2 = dog(img, MID[0] * s, MID[1] * s).astype(np.float64) ** 2
    H, W = img.shape
    out = np.full((len(ye_m) - 1, len(xe_m) - 1, 3), np.nan)
    oob = 0
    for i in range(len(ye_m) - 1):
        y0 = int(round(s * ye_m[i] + t[1])); y1 = int(round(s * ye_m[i + 1] + t[1]))
        cy0, cy1 = max(0, y0), min(H, y1)
        for j in range(len(xe_m) - 1):
            x0 = int(round(s * xe_m[j] + t[0])); x1 = int(round(s * xe_m[j + 1] + t[0]))
            cx0, cx1 = max(0, x0), min(W, x1)
            if cy1 - cy0 < 8 or cx1 - cx0 < 8:
                oob += 1; continue
            if (y0, y1, x0, x1) != (cy0, cy1, cx0, cx1):
                oob += 1
            sl = (slice(cy0, cy1), slice(cx0, cx1))
            out[i, j, 0] = img[sl].mean()
            out[i, j, 1] = np.sqrt(f2[sl].mean())
            out[i, j, 2] = np.sqrt(m2[sl].mean())
    return out, oob


def noise_floor(mean_lv, rms, nbin=10, pct=10.0):
    """Lower envelope of band RMS against tile mean level = the level-dependent
    noise floor (shot noise scales with level, so one global floor is wrong)."""
    v = np.isfinite(mean_lv) & np.isfinite(rms)
    if v.sum() < 20:
        return np.full(rms.shape, np.nanpercentile(rms, pct) if v.any() else 0.0)
    lv, r = mean_lv[v], rms[v]
    edges = np.unique(np.quantile(lv, np.linspace(0, 1, nbin + 1)))
    cx, cy = [], []
    for b in range(len(edges) - 1):
        sel = (lv >= edges[b]) & (lv <= edges[b + 1])
        if sel.sum() >= 5:
            cx.append(lv[sel].mean()); cy.append(np.percentile(r[sel], pct))
    if len(cx) < 2:
        return np.full(rms.shape, np.percentile(r, pct))
    return np.interp(mean_lv, np.asarray(cx), np.asarray(cy))


def corrected(mean_lv, rms):
    fl = noise_floor(mean_lv, rms)
    return np.sqrt(np.maximum(rms ** 2 - fl ** 2, 0.0)), fl


