"""V-GATHER instruments: my own implementations of the two ringing statistics,
plus a third that measures the band the gather flip can actually reach.

A  = STEP-NORMALISED MEDIAN OVERSHOOT, the family orch_halo.py uses.
     Profiles along the gradient normal, each divided by its own step, median
     across profiles, peak excursion beyond [0,1] inside a BAND of distances.
     orch_halo runs it at DS=2 with BAND=(8,90) DOWNSAMPLED px, i.e. 16..180
     FULL-RES px from the edge centre.
B  = LOCAL-ENVELOPE RING FRACTION, orch_abpair.py's overshoot_frac verbatim in
     form: fraction of |y - boxblur10(y)| above 3x ITS OWN std.
C  = NEAR-EDGE OVERSHOOT: A's machinery with DS=1 and BAND=(1,4) full-res px,
     which is where a Catmull-Rom or Malvar negative lobe actually lands.
"""
import numpy as np

# ---------------------------------------------------------------- helpers
def boxblur(a, win):
    r = win // 2
    pad = np.pad(a, ((r, r), (r, r)), mode="edge")
    c = np.cumsum(np.cumsum(pad, axis=0), axis=1)
    c = np.pad(c, ((1, 0), (1, 0)))
    h, w = a.shape
    s = (c[win:win + h, win:win + w] - c[0:h, win:win + w]
         - c[win:win + h, 0:w] + c[0:h, 0:w])
    return s / (win * win)


def downsample(a, f):
    if f == 1:
        return a
    h, w = a.shape[0] // f * f, a.shape[1] // f * f
    return a[:h, :w].reshape(h // f, f, w // f, f).mean(axis=(1, 3))


def bilinear(img, ys, xs):
    h, w = img.shape
    ys = np.clip(ys, 0, h - 1.001)
    xs = np.clip(xs, 0, w - 1.001)
    y0 = ys.astype(np.int32); x0 = xs.astype(np.int32)
    fy = ys - y0; fx = xs - x0
    return (img[y0, x0] * (1 - fy) * (1 - fx) + img[y0 + 1, x0] * fy * (1 - fx)
            + img[y0, x0 + 1] * (1 - fy) * fx + img[y0 + 1, x0 + 1] * fy * fx)


# ------------------------------------------------- A / C : step overshoot
def step_overshoot(img, half, band, blur=9, edge_pct=99.5, max_prof=4000,
                   min_step_frac=0.08, plateau_frac=0.18, seed=0, ds=1,
                   shuffle=False, pts_override=None):
    """Peak excursion of the MEDIAN step-normalised profile beyond [0,1]."""
    img = downsample(np.asarray(img, np.float64), ds)
    rng = np.random.default_rng(seed)
    b = boxblur(img, blur)
    gy = np.zeros_like(b); gx = np.zeros_like(b)
    gy[1:-1, :] = (b[2:, :] - b[:-2, :]) * 0.5
    gx[:, 1:-1] = (b[:, 2:] - b[:, :-2]) * 0.5
    mag = np.hypot(gy, gx)
    m = np.zeros(mag.shape, bool)
    m[half + 2:-half - 2, half + 2:-half - 2] = True
    thr = float(np.percentile(mag[m], edge_pct))
    if pts_override is not None:
        ys, xs = pts_override
    else:
        ys, xs = np.nonzero((mag >= thr) & m)
        if ys.size > max_prof:
            k = rng.choice(ys.size, max_prof, replace=False)
            ys, xs = ys[k], xs[k]
    lo_p, hi_p = np.percentile(img, (1.0, 99.0))
    min_step = min_step_frac * float(hi_p - lo_p)
    t = np.arange(-half, half + 1, dtype=np.float64)
    nflat = max(3, half // 7)
    keep = []; rej = 0
    for py, px in zip(ys.tolist(), xs.tolist()):
        if shuffle:
            ang = rng.uniform(0, 2 * np.pi)
            ny, nx = np.sin(ang), np.cos(ang)
            py = int(rng.integers(half + 2, img.shape[0] - half - 2))
            px = int(rng.integers(half + 2, img.shape[1] - half - 2))
        else:
            g = float(np.hypot(gy[py, px], gx[py, px]))
            if g <= 0:
                rej += 1; continue
            ny, nx = gy[py, px] / g, gx[py, px] / g
        v = bilinear(img, py + t * ny, px + t * nx)
        lo = float(v[:nflat].mean()); hi = float(v[-nflat:].mean())
        step = abs(hi - lo)
        if step < min_step:
            rej += 1; continue
        q = max(4, half // 5)
        lf = abs(float(v[:q].mean()) - float(v[q:2 * q].mean()))
        rf = abs(float(v[-q:].mean()) - float(v[-2 * q:-q].mean()))
        if max(lf, rf) > plateau_frac * step:
            rej += 1; continue
        p = (v - lo) / (hi - lo)
        if hi < lo:
            p = p[::-1]
        keep.append(p)
    if not keep:
        return dict(over=float("nan"), over_hi=float("nan"), over_lo=float("nan"),
                    n=0, rej=rej, prof=None)
    prof = np.median(np.stack(keep), axis=0)
    c = half; a, bb = band
    over_hi = float(np.max(prof[c + a:c + bb + 1]) - 1.0)
    over_lo = float(0.0 - np.min(prof[c - bb:c - a + 1]))
    return dict(over=max(over_hi, over_lo), over_hi=over_hi, over_lo=over_lo,
                n=len(keep), rej=rej, prof=prof)


def A_stat(img, seed=0):
    """orch_halo's configuration: DS=2, HALF=100, BAND=(8,90)."""
    return step_overshoot(img, half=100, band=(8, 90), ds=2, seed=seed)


def C_stat(img, seed=0):
    """Near-edge: DS=1, HALF=24, BAND=(1,4) full-res px."""
    return step_overshoot(img, half=24, band=(1, 4), ds=1, blur=5, seed=seed)


# ------------------------------------------------ B : envelope ring frac
def B_stat(y):
    """orch_abpair.overshoot_frac, verbatim in form."""
    y = np.asarray(y, np.float64)
    k = 5
    c = np.cumsum(np.pad(y, ((0, 0), (k, k)), mode="edge"), axis=1)
    h = (c[:, 2 * k:] - c[:, :-2 * k]) / (2 * k)
    c = np.cumsum(np.pad(h, ((k, k), (0, 0)), mode="edge"), axis=0)
    b = (c[2 * k:, :] - c[:-2 * k, :]) / (2 * k)
    d = y - b
    s = d.std()
    return float((np.abs(d) > 3.0 * s).mean()) if s > 0 else 0.0


def luma(rgb):
    return (0.2126 * rgb[:, :, 0] + 0.7152 * rgb[:, :, 1]
            + 0.0722 * rgb[:, :, 2])


def edge_energy(y):
    gy = np.abs(np.diff(y, axis=0)[:, :-1])
    gx = np.abs(np.diff(y, axis=1)[:-1, :])
    return float((gy + gx).mean())
