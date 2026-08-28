r"""Independent lateral-CA displacement estimator for the V6 re-render.

Written for V-REVIEW WITHOUT reference to BUILD-CROP's cafit.py/carefit.py,
which fitted the coefficient under test. Scoring a fit with the estimator that
produced it checks the fit against itself.

PRIMARY STATISTIC  signed radial displacement of R (and B) relative to G, in
sensels and in ppm of radius. Sign-symmetric by construction: an error either
way raises |d|, so an over-correction cannot look like a fix. This is exactly
the property the "1.82x magenta" counter lacked.

Sign convention: the edge normal n is flipped to point OUTWARD from the optical
centre, so s > 0 means that channel's edge sits FURTHER OUT than green's.
"""
import numpy as np, tifffile
from scipy.ndimage import map_coordinates

# ---- absolute qualification floors. A picker that cannot reject is not a picker.
TILE        = 64
GRAD_FLOOR  = 300.0   # DN, mean |grad G| inside the tile
COH_MIN     = 0.55    # structure-tensor coherence: is there ONE straight edge
ALIGN_MIN   = 0.70    # |n . rhat|: edge normal must be near-radial to constrain d
R_MIN_FRAC  = 0.25    # lateral CA vanishes at the centre; near-centre = noise
MIN_SITES   = 12      # fewer than this -> UNSCORED, never "clean"
HALF        = 24      # profile half-length in sensels
PERP        = 12      # half-width averaged along the edge
LAGS        = np.arange(-3.0, 3.0001, 0.02)


def load(path):
    a = tifffile.imread(path)
    if a.ndim != 3 or a.shape[2] != 3:
        raise SystemExit("unexpected shape %r for %s" % (a.shape, path))
    return a


def sites(G, centre):
    """Qualifying edge sites. Absolute floors only -- no top-N ranking."""
    gy, gx = np.gradient(G.astype(np.float32))
    H, W = G.shape
    cy, cx = centre
    rmax = np.hypot(max(cy, H - cy), max(cx, W - cx))
    out = []
    ny_, nx_ = H // TILE, W // TILE
    for by in range(1, ny_ - 1):
        for bx in range(1, nx_ - 1):
            ys, xs = by * TILE, bx * TILE
            ax = gx[ys:ys+TILE, xs:xs+TILE]
            ay = gy[ys:ys+TILE, xs:xs+TILE]
            m = float(np.mean(np.hypot(ax, ay)))
            if m < GRAD_FLOOR:
                continue
            Jxx = float(np.sum(ax*ax)); Jyy = float(np.sum(ay*ay))
            Jxy = float(np.sum(ax*ay))
            tr = Jxx + Jyy
            if tr <= 0:
                continue
            coh = np.sqrt((Jxx-Jyy)**2 + 4*Jxy**2) / tr
            if coh < COH_MIN:
                continue
            th = 0.5*np.arctan2(2*Jxy, Jxx-Jyy)
            n = np.array([np.cos(th), np.sin(th)])        # (x, y), gradient dir
            py, px = ys + TILE/2.0, xs + TILE/2.0
            rv = np.array([px - cx, py - cy])
            r = float(np.hypot(*rv))
            if r < R_MIN_FRAC * rmax:
                continue
            rhat = rv / r
            al = float(np.dot(n, rhat))
            if abs(al) < ALIGN_MIN:
                continue
            if al < 0:
                n = -n                                     # make n point OUTWARD
                al = -al
            out.append((py, px, n[0], n[1], r, m, al))
    return out


def profile(img_c, py, px, nx, ny):
    """Mean intensity along the outward normal, sampled by interpolation.

    DEFECT FIXED: the previous implementation binned pixels by `digitize` into
    unit bins of t. That is orientation-dependent -- at 0/90 deg each bin takes a
    clean row/column, but at 45 deg the projections land at multiples of 0.707
    and alias against the unit bins. Commissioning measured the resulting gain as
    1.000 at 0 deg, 0.936 at 20/70 deg and **0.170 at 45 deg**. Sampling on an
    explicit (t, u) lattice with cubic interpolation is orientation-independent.
    """
    mx, my = -ny, nx                      # unit vector perpendicular to n
    ts = np.arange(-HALF, HALF + 1, 1.0)
    us = np.arange(-PERP, PERP + 1, 1.0)
    T, U = np.meshgrid(ts, us)
    ys = py + T * ny + U * my
    xs = px + T * nx + U * mx
    m = int(HALF + PERP + 4)
    y0, y1 = int(py) - m, int(py) + m + 1
    x0, x1 = int(px) - m, int(px) + m + 1
    if y0 < 0 or x0 < 0 or y1 > img_c.shape[0] or x1 > img_c.shape[1]:
        return None
    win = img_c[y0:y1, x0:x1].astype(np.float32)
    v = map_coordinates(win, [(ys - y0).ravel(), (xs - x0).ravel()],
                        order=3, mode="nearest")
    return v.reshape(U.shape).mean(axis=0).astype(np.float32)


def shift(pa, pb):
    """Sub-pixel lag s such that pa(t+s) best matches pb(t). Uses the derivative
    so a channel offset/gain cannot masquerade as a displacement."""
    da = np.diff(pa.astype(np.float64)); db = np.diff(pb.astype(np.float64))
    if np.std(da) < 1e-6 or np.std(db) < 1e-6:
        return None
    da = (da - da.mean()) / np.std(da)
    db = (db - db.mean()) / np.std(db)
    t = np.arange(len(da), dtype=np.float64)
    best, bs = -2.0, None
    for s in LAGS:
        ai = np.interp(t + s, t, da, left=np.nan, right=np.nan)
        m = ~np.isnan(ai)
        if m.sum() < len(t) - 8:
            continue
        aa = ai[m] - ai[m].mean(); bb = db[m] - db[m].mean()
        den = np.linalg.norm(aa) * np.linalg.norm(bb)
        if den <= 0:
            continue
        c = float(np.dot(aa, bb) / den)
        if c > best:
            best, bs = c, float(s)
    if bs is None or best < 0.90:      # weak match -> refuse to vote
        return None
    return bs


def measure(img, centre=None, want_sites=None):
    H, W = img.shape[:2]
    centre = centre or (H/2.0, W/2.0)
    G = img[:, :, 1]
    S = want_sites if want_sites is not None else sites(G, centre)
    dR, dB, ppmR, ppmB, used = [], [], [], [], []
    for (py, px, nx, ny, r, m, al) in S:
        pg = profile(img[:, :, 1], py, px, nx, ny)
        pr = profile(img[:, :, 0], py, px, nx, ny)
        pb = profile(img[:, :, 2], py, px, nx, ny)
        if pg is None or pr is None or pb is None:
            continue
        sr = shift(pr, pg); sb = shift(pb, pg)
        if sr is None or sb is None:
            continue
        sr /= al; sb /= al          # normal component -> radial displacement
        dR.append(sr); dB.append(sb)
        ppmR.append(sr / r * 1e6); ppmB.append(sb / r * 1e6)
        used.append((py, px, nx, ny, r, m, al))
    return dict(n_sites=len(S), n_used=len(dR),
                dR=np.array(dR), dB=np.array(dB),
                ppmR=np.array(ppmR), ppmB=np.array(ppmB), used=used)


def summarise(res):
    if res["n_used"] < MIN_SITES:
        return dict(verdict="UNSCORED", n_used=res["n_used"])
    def med(a): return float(np.median(a))
    def mad(a): return float(np.median(np.abs(a - np.median(a))) * 1.4826)
    agree = float(np.mean(np.sign(res["dR"]) == np.sign(res["dB"])))
    return dict(verdict="SCORED", n_used=res["n_used"],
                dR=med(res["dR"]), dR_mad=mad(res["dR"]),
                dB=med(res["dB"]), dB_mad=mad(res["dB"]),
                ppmR=med(res["ppmR"]), ppmR_mad=mad(res["ppmR"]),
                ppmB=med(res["ppmB"]), ppmB_mad=mad(res["ppmB"]),
                absR=med(np.abs(res["dR"])), absB=med(np.abs(res["dB"])),
                agree=agree)
