"""V-SOFTCHECK -- independent re-derivation of the "merged master vs per-site
complete-bracket ceiling" ratio.

WRITTEN FROM SCRATCH.  Nothing here is derived from corpus_softness.py or
envelope_null.py, neither of which has been opened by this lane.

DESIGN
------
gauge   Both sides of the ratio are produced by ONE binary (pin 9b05d0b7,
        sha256 44C2F2CD...F490) with ONE flag set.  The master is
        `strehl stack <dir>`; reference member k is the SAME command with
        STREHL_ONLY_FRAME=k.  Same demosaic/bin, same colour handling, same
        alignment stage, same resampler, no exposure gain, no tone curve.
        There is no second developer anywhere in the pipeline.

stat    Per tile, mean squared response of an isotropic band-pass
        DoG(s1,s2) applied to luma.
          E_mid = <DoG(0.7,1.4)^2>   -- the detail band (peak ~0.219 cyc/px)
          E_hi  = <DoG(0.35,0.7)^2>  -- the top band (peak ~0.437 cyc/px),
                                        used only as a white-noise proxy
        Arm NOSUB : S = E_mid
        Arm SUB   : S = E_mid - (g_mid/g_hi) * E_hi,  g_* = analytic white-
                    noise gain of each filter.  NOT clamped at zero (a
                    max(0,.) is how a bounded estimator hides its own sign).

ratio   r_t = S(master, t) / max_k S(frame_k, t)   over EVERY k in 0..N-1.
        Headline = median over selected tiles; 95% CI by 4x4-block bootstrap.

geometry The master is aligned to its own reference frame with a coverage
        rescale; a 1-frame render is aligned to itself with a different
        coverage rescale.  So frame k must be registered to the master.
        Registration is by phase correlation on 512^2 anchors + a 6-parameter
        affine displacement fit.  The reference tile is then read at an
        INTEGER offset -- no interpolation ever touches the reference, so the
        instrument cannot blur its own denominator.
"""
import sys, os, json, math, time
import numpy as np
import tifffile
from scipy import ndimage
from numpy.fft import rfft2, irfft2, fft2, ifft2

ROOT = r"C:\dev\strehl-out\V-SOFTCHECK"

# ---------------------------------------------------------------- filters
S_MID = (0.7, 1.4)
S_HI  = (0.35, 0.7)
S_LOW = (3.0, 6.0)

def _white_gain(s1, s2, n=2048):
    """integral of |H|^2 over the unit sampling cell, H = DoG transfer fn."""
    f = (np.arange(n) + 0.5) / n - 0.5
    fx, fy = np.meshgrid(f, f, indexing="xy")
    r2 = fx * fx + fy * fy
    H = np.exp(-2 * np.pi**2 * s1**2 * r2) - np.exp(-2 * np.pi**2 * s2**2 * r2)
    return float((H * H).mean())

G_MID = _white_gain(*S_MID)
G_HI  = _white_gain(*S_HI)
C_NOISE = G_MID / G_HI

def dog(img, s):
    return ndimage.gaussian_filter(img, s[0], mode="reflect") - \
           ndimage.gaussian_filter(img, s[1], mode="reflect")

# ---------------------------------------------------------------- io
def load_luma(path, gauge):
    a = tifffile.imread(path)
    assert a.ndim == 3 and a.shape[2] == 3, (path, a.shape)
    a = a.astype(np.float32)
    # camera-native binned RGB: R=R, G=(G1+G2)/2, B=B  -> Bayer-natural luma
    return 0.25 * a[:, :, 0] + 0.5 * a[:, :, 1] + 0.25 * a[:, :, 2]

# ---------------------------------------------------------------- integral tiles
def tile_means(x, oy, ox, T):
    """mean of x over tiles with per-tile integer origins oy, ox (vectors)."""
    c = np.cumsum(np.cumsum(x, axis=0, dtype=np.float64), axis=1)
    c = np.pad(c, ((1, 0), (1, 0)))
    a = c[oy + T, ox + T] - c[oy, ox + T] - c[oy + T, ox] + c[oy, ox]
    return a / (T * T)

# ---------------------------------------------------------------- registration
def _prep(p):
    p = p - ndimage.gaussian_filter(p, 8.0, mode="reflect")
    n = p.shape[0]
    w = np.hanning(n)
    return p * w[:, None] * w[None, :]

def phase_shift(A, B):
    """shift (dy,dx) that maps B onto A, integer, by phase correlation."""
    Fa = fft2(_prep(A)); Fb = fft2(_prep(B))
    R = Fa * np.conj(Fb)
    m = np.abs(R); m[m == 0] = 1
    c = np.real(ifft2(R / m))
    n = c.shape[0]
    i = np.unravel_index(np.argmax(c), c.shape)
    peak = c[i]
    dy = i[0] if i[0] <= n // 2 else i[0] - n
    dx = i[1] if i[1] <= n // 2 else i[1] - n
    # peak quality: peak over rms of the rest
    q = peak / (c.std() + 1e-12)
    return -dy, -dx, q          # displacement of frame relative to master

def register(M, F, win=512, ny=4, nx=6, margin=64):
    H, W = M.shape
    ys = np.linspace(margin, H - win - margin, ny).astype(int)
    xs = np.linspace(margin, W - win - margin, nx).astype(int)
    pts, dsp, qs = [], [], []
    for y in ys:
        for x in xs:
            dy, dx, q = phase_shift(M[y:y+win, x:x+win], F[y:y+win, x:x+win])
            pts.append((y + win/2, x + win/2)); dsp.append((dy, dx)); qs.append(q)
    pts = np.array(pts, float); dsp = np.array(dsp, float); qs = np.array(qs, float)
    keep = qs > 6.0
    if keep.sum() < 8:
        keep = qs >= np.sort(qs)[-8]
    A = np.column_stack([np.ones(len(pts)), pts[:, 0], pts[:, 1]])
    coef = None
    for _ in range(6):
        w = keep.astype(float)
        if coef is not None:
            r = np.linalg.norm(dsp - A @ coef, axis=1)
            s = 1.4826 * np.median(r[keep]) + 1e-6
            w = keep.astype(float) * np.clip(2.0 * s / np.maximum(r, 1e-9), 0, 1)
        Aw = A * w[:, None]
        coef, *_ = np.linalg.lstsq(Aw, dsp * w[:, None], rcond=None)
    r = np.linalg.norm(dsp - A @ coef, axis=1)
    return coef, float(np.sqrt(np.mean(r[keep]**2))), int(keep.sum()), len(pts)

def disp_at(coef, cy, cx):
    A = np.column_stack([np.ones(len(cy)), cy, cx])
    return A @ coef     # (n,2) -> dy, dx

# ---------------------------------------------------------------- plants
def plant_blur(x, sigma):
    return ndimage.gaussian_filter(x, sigma, mode="reflect")

def plant_sharpen(x, amount, sigma):
    return x + amount * (x - ndimage.gaussian_filter(x, sigma, mode="reflect"))

def plant_gain(x, g):
    return x * g

def apply_plant(x, spec, rng=None):
    if spec is None or spec[0] == "none":
        return x
    k = spec[0]
    if k == "blur":     return plant_blur(x, spec[1])
    if k == "sharpen":  return plant_sharpen(x, spec[1], spec[2])
    if k == "gain":     return plant_gain(x, spec[1])
    if k == "noise":    return x + spec[1] * rng.standard_normal(x.shape).astype(np.float32)
    raise ValueError(spec)

# ---------------------------------------------------------------- core
def build_grid(H, W, T, step, margin):
    ys = np.arange(margin, H - margin - T + 1, step)
    xs = np.arange(margin, W - margin - T + 1, step)
    gy, gx = np.meshgrid(ys, xs, indexing="ij")
    return gy.ravel(), gx.ravel(), gy.shape

def stats_of(img, oy, ox, T):
    m  = tile_means(dog(img, S_MID)**2, oy, ox, T)
    h  = tile_means(dog(img, S_HI)**2,  oy, ox, T)
    lo = tile_means(dog(img, S_LOW)**2, oy, ox, T)
    lv = tile_means(img, oy, ox, T)
    return m, h, lo, lv

def measure(subject, gauge="lin", T=128, step=64, margin=160,
            master_plant=None, ref_plant=None, ref_offset=(0, 0),
            null_mode=None, seed=0, frames=None, verbose=True,
            master_override=None):
    """returns dict with ratios in both arms."""
    d = os.path.join(ROOT, gauge, subject)
    fl = sorted(f for f in os.listdir(d) if f.startswith("f") and f.endswith(".tiff"))
    if frames is not None:
        fl = [fl[i] for i in frames]
    N = len(fl)
    rng = np.random.default_rng(seed)

    M = load_luma(os.path.join(d, "master.tiff"), gauge) if master_override is None \
        else master_override.copy()
    H, W = M.shape
    oy, ox, shape = build_grid(H, W, T, step, margin)
    cy = oy + T / 2.0; cx = ox + T / 2.0

    Mp = apply_plant(M, master_plant, rng)
    m_mid, m_hi, m_lo, m_lv = stats_of(Mp, oy, ox, T)

    best_mid = np.full(len(oy), -np.inf)
    best_sub = np.full(len(oy), -np.inf)
    ref_lv_sum = np.zeros(len(oy)); ref_hi_sum = np.zeros(len(oy))
    reg = []
    for k, fn in enumerate(fl):
        if null_mode == "identical":
            F = M.copy(); coef = np.zeros((3, 2)); rms, kp, tot = 0.0, 0, 0
        elif null_mode == "noised":
            F = M + null_sigma_map(d, gauge, M, oy, ox, T, shape) * \
                rng.standard_normal(M.shape).astype(np.float32)
            coef = np.zeros((3, 2)); rms, kp, tot = 0.0, 0, 0
        else:
            F = load_luma(os.path.join(d, fn), gauge)
            coef, rms, kp, tot = register(M, F)
        reg.append((fn, coef.tolist(), rms, kp, tot))
        Fp = apply_plant(F, ref_plant, rng)
        dd = disp_at(coef, cy, cx)
        ry = np.round(oy + dd[:, 0]).astype(int) + ref_offset[0]
        rx = np.round(ox + dd[:, 1]).astype(int) + ref_offset[1]
        ry = np.clip(ry, 0, H - T); rx = np.clip(rx, 0, W - T)
        f_mid, f_hi, f_lo, f_lv = stats_of(Fp, ry, rx, T)
        best_mid = np.maximum(best_mid, f_mid)
        best_sub = np.maximum(best_sub, f_mid - C_NOISE * f_hi)
        ref_lv_sum += f_lv; ref_hi_sum += f_hi
        if verbose:
            print(f"  {fn}  reg rms={rms:5.2f}px kept={kp}/{tot} "
                  f"scale_y={1+coef[1,0]:.5f} scale_x={1+coef[2,1]:.5f} "
                  f"t=({coef[0,0]:+.1f},{coef[0,1]:+.1f})", flush=True)

    m_sub = m_mid - C_NOISE * m_hi
    out = dict(subject=subject, gauge=gauge, N=N, T=T, step=step, n_tiles=int(len(oy)),
               c_noise=C_NOISE, reg=reg,
               level_ratio=float(np.median(m_lv / (ref_lv_sum / N))),
               noisefloor_ratio=float(np.median(m_hi / (ref_hi_sum / N))))
    # tile selection on a focus-insensitive quantity: coarse-band energy
    lo = m_lo
    thr = np.quantile(lo, 0.50)
    sel = lo >= thr
    out["sel_thr_q50"] = float(thr)
    for arm, mv, bv in (("NOSUB", m_mid, best_mid), ("SUB", m_sub, best_sub)):
        ok = sel & (bv > 0) & np.isfinite(bv) & np.isfinite(mv)
        r = mv[ok] / bv[ok]
        out[arm] = dict(
            n=int(ok.sum()), dropped=int(sel.sum() - ok.sum()),
            median=float(np.median(r)), mean=float(np.mean(r)),
            agg=float(mv[ok].sum() / bv[ok].sum()),
            ci=block_ci(r, ok, shape, len(oy)),
            frac_gt1=float((r > 1).mean()))
        # flat control: the other half of the tiles
        okf = (~sel) & (bv > 0)
        rf = mv[okf] / bv[okf]
        out[arm]["flat_median"] = float(np.median(rf)) if okf.sum() else None
        # quintiles of coarse-band energy
        q = np.quantile(lo, [0.2, 0.4, 0.6, 0.8])
        b = np.digitize(lo, q)
        out[arm]["quintiles"] = [
            float(np.median((mv / np.where(bv > 0, bv, np.nan))[(b == i)]))
            for i in range(5)]
    return out

def block_ci(r, ok, shape, ntot, B=2000, block=4, seed=7):
    idx = np.arange(ntot).reshape(shape)
    by = int(np.ceil(shape[0] / block)); bx = int(np.ceil(shape[1] / block))
    blocks = []
    full = np.zeros(ntot, bool); full[np.where(ok)[0]] = True
    for i in range(by):
        for j in range(bx):
            ids = idx[i*block:(i+1)*block, j*block:(j+1)*block].ravel()
            ids = ids[full[ids]]
            if len(ids): blocks.append(ids)
    if not blocks: return [None, None]
    vals = np.full(ntot, np.nan); vals[np.where(ok)[0]] = r
    rng = np.random.default_rng(seed)
    meds = np.empty(B)
    for b in range(B):
        pick = rng.integers(0, len(blocks), len(blocks))
        v = np.concatenate([blocks[p] for p in pick])
        meds[b] = np.median(vals[v])
    return [float(np.percentile(meds, 2.5)), float(np.percentile(meds, 97.5))]

_SIGMA_CACHE = {}
def null_sigma_map(d, gauge, M, oy, ox, T, shape):
    """per-pixel sigma whose top-band energy matches the real frames' median."""
    key = (d, T)
    if key in _SIGMA_CACHE: return _SIGMA_CACHE[key]
    fl = sorted(f for f in os.listdir(d) if f.startswith("f") and f.endswith(".tiff"))
    acc = []
    for fn in fl:
        F = load_luma(os.path.join(d, fn), gauge)
        acc.append(tile_means(dog(F, S_HI)**2, oy, ox, T))
    med = np.median(np.array(acc), axis=0)
    sig = np.sqrt(np.maximum(med, 0) / G_HI).reshape(shape)
    zy = M.shape[0] / sig.shape[0]; zx = M.shape[1] / sig.shape[1]
    smap = ndimage.zoom(sig, (zy, zx), order=1).astype(np.float32)
    smap = smap[:M.shape[0], :M.shape[1]]
    if smap.shape != M.shape:
        smap = np.pad(smap, ((0, M.shape[0]-smap.shape[0]), (0, M.shape[1]-smap.shape[1])), mode="edge")
    _SIGMA_CACHE[key] = smap
    return smap
