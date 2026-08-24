"""M107-chroma common: RAW decode and per-channel edge-spread fitting.

Rule 32: `raw_image_visible` is a view into LibRaw's buffer. Every decode here
allocates AND copies inside the `with` block.

Rule 7: never compute statistics over the full decoded buffer. `raw_image_visible`
is already the active area, which is what rule 7 asks for; we assert its shape.

Geometry convention, stated once and used everywhere:

    sensel (x, y), RGGB, matching `CfaPlane::rggb_at`
        R  at (2px,   2py  )
        G1 at (2px+1, 2py  )
        G2 at (2px,   2py+1)
        B  at (2px+1, 2py+1)

so every plane sample carries a true sensel coordinate and CO-SITING IS HANDLED
BY CONSTRUCTION. Any per-channel displacement this module reports is therefore
NOT the CFA lattice.
"""

import json
import os

import numpy as np
import rawpy
from scipy.optimize import curve_fit
from scipy.special import erf

MACRO = r"D:\personal\macro"
OUT = r"C:\dev\strehl-out\M107-chroma"

# sensel offsets of each plane's sample within its 2x2 quad, (dx, dy)
TRUE_OFFSET = {"R": (0.0, 0.0), "G1": (1.0, 0.0), "G2": (0.0, 1.0), "B": (1.0, 1.0)}
# the table the INSTRUMENT uses; C6 patches this one to prove what it removes.
PLANE_OFFSET = dict(TRUE_OFFSET)
PLANES = ("R", "G1", "G2", "B")


def frames(stack):
    d = os.path.join(MACRO, stack)
    return sorted(os.path.join(d, f) for f in os.listdir(d) if f.lower().endswith(".arw"))


def decode(path):
    """Full active-area CFA as float32. Copy is made inside the `with` (rule 32)."""
    with rawpy.imread(path) as r:
        cfa = r.raw_image_visible.astype(np.float32)  # allocate AND copy inside
        black = float(np.mean(r.black_level_per_channel))
        pattern = r.raw_pattern.copy()
    return cfa - black, black, pattern


def decode_roi(path, x0, y0, w, h):
    """Sensel-space ROI. x0,y0 must be EVEN so the RGGB phase is preserved."""
    assert x0 % 2 == 0 and y0 % 2 == 0, "ROI origin must be quad-aligned"
    with rawpy.imread(path) as r:
        roi = r.raw_image_visible[y0 : y0 + h, x0 : x0 + w].astype(np.float32)
        black = float(np.mean(r.black_level_per_channel))
    return roi - black


def planes_of(roi):
    """Split a quad-aligned sensel ROI into the four CFA planes."""
    return {
        "R": roi[0::2, 0::2],
        "G1": roi[0::2, 1::2],
        "G2": roi[1::2, 0::2],
        "B": roi[1::2, 1::2],
    }


def plane_coords(plane, ny, nx, x0=0, y0=0):
    """True sensel coordinates of every sample of `plane`, shape (ny,nx) each."""
    dx, dy = PLANE_OFFSET[plane]
    xs = x0 + 2.0 * np.arange(nx, dtype=np.float64) + dx
    ys = y0 + 2.0 * np.arange(ny, dtype=np.float64) + dy
    return np.meshgrid(xs, ys)


# ---------------------------------------------------------------- edge fitting


def edge_line_from_green(roi):
    """Estimate the edge line (unit normal n, point p) from the GREEN planes only.

    Blind to R and B by construction, so the line is not fitted on the channels
    whose displacement we are about to measure.
    """
    g1, g2 = roi[0::2, 1::2], roi[1::2, 0::2]
    ny = min(g1.shape[0], g2.shape[0])
    nx = min(g1.shape[1], g2.shape[1])
    g = 0.5 * (g1[:ny, :nx] + g2[:ny, :nx])
    gy, gx = np.gradient(g.astype(np.float64))
    mag = np.hypot(gx, gy)
    thr = np.percentile(mag, 90.0)
    m = mag >= thr
    if m.sum() < 32 or not np.isfinite(mag[m]).all() or (mag[m] ** 2).sum() <= 0:
        return None
    # Orientation by the doubled-angle (structure tensor) mean, which is
    # 180-degree ambiguous exactly as a line orientation is.
    ang2 = np.arctan2(2 * gx[m] * gy[m], gx[m] ** 2 - gy[m] ** 2)
    w = mag[m] ** 2
    a = 0.5 * np.arctan2((w * np.sin(ang2)).sum(), (w * np.cos(ang2)).sum())
    n = np.array([np.cos(a), np.sin(a)])  # unit normal in PLANE units
    yy, xx = np.nonzero(m)
    # centroid in sensel units (green mean sits at the quad centre: +0.5,+0.5)
    px = 2.0 * (w * xx).sum() / w.sum() + 0.5
    py = 2.0 * (w * yy).sum() / w.sum() + 0.5
    contrast = float(np.percentile(g, 98) - np.percentile(g, 2))
    return n, np.array([px, py]), contrast, float(a)


def _erf_edge(d, a, b, d0, w):
    return a + b * erf((d - d0) / (np.sqrt(2.0) * np.abs(w)))


def fit_plane_esf(vals, X, Y, n, p, dmax=12.0):
    """Fit a + b*erf((d-d0)/(sqrt2 w)) to one plane's samples projected on `n`.

    Returns dict with d0 (sensel), w (sensel sigma), amplitude, rms residual.
    """
    d = (X - p[0]) * n[0] + (Y - p[1]) * n[1]
    v = vals.astype(np.float64)
    keep = np.abs(d) <= dmax
    d, v = d[keep].ravel(), v[keep].ravel()
    if d.size < 64:
        return None
    lo, hi = np.percentile(v, 2), np.percentile(v, 98)
    a0 = 0.5 * (lo + hi)
    b0 = 0.5 * (hi - lo)
    # sign: let the fit choose, seed from the correlation of v with d
    if np.corrcoef(d, v)[0, 1] < 0:
        b0 = -b0
    try:
        popt, _ = curve_fit(
            _erf_edge, d, v, p0=[a0, b0, 0.0, 2.0], maxfev=40000
        )
    except Exception:
        return None
    a, b, d0, w = popt
    resid = v - _erf_edge(d, a, b, d0, w)
    return {
        "d0": float(d0),
        "w": float(abs(w)),
        "amp": float(abs(2 * b)),
        "rms": float(np.sqrt(np.mean(resid**2))),
        "n": int(d.size),
    }


def esf_all_planes(roi, x0=0, y0=0, dmax=12.0):
    """Instrument A. Returns per-plane {d0, w, ...} plus the fitted edge line."""
    line = edge_line_from_green(roi)
    if line is None:
        return None
    n, p, contrast, ang = line
    p = np.array([p[0] + x0, p[1] + y0])
    out = {"normal": [float(n[0]), float(n[1])], "point": [float(p[0]), float(p[1])],
           "contrast": contrast, "angle_rad": ang, "planes": {}}
    pl = planes_of(roi)
    for name in PLANES:
        v = pl[name]
        X, Y = plane_coords(name, v.shape[0], v.shape[1], x0, y0)
        f = fit_plane_esf(v, X, Y, n, p, dmax=dmax)
        if f is None:
            return None
        out["planes"][name] = f
    return out


def summarise(esf):
    """Per-channel offsets against the green mean, plus the G1-G2 internal null."""
    P = esf["planes"]
    gd0 = 0.5 * (P["G1"]["d0"] + P["G2"]["d0"])
    gw = 0.5 * (P["G1"]["w"] + P["G2"]["w"])
    return {
        "dR": P["R"]["d0"] - gd0,
        "dB": P["B"]["d0"] - gd0,
        "dRB": P["R"]["d0"] - P["B"]["d0"],
        "null_dG": P["G1"]["d0"] - P["G2"]["d0"],
        "wR": P["R"]["w"] - gw,
        "wB": P["B"]["w"] - gw,
        "null_wG": P["G1"]["w"] - P["G2"]["w"],
        "wG": gw,
        "w_abs": {k: P[k]["w"] for k in PLANES},
        "d0_abs": {k: P[k]["d0"] for k in PLANES},
        "rms": {k: P[k]["rms"] for k in PLANES},
        "amp": {k: P[k]["amp"] for k in PLANES},
        "contrast": esf["contrast"],
        "normal": esf["normal"],
        "point": esf["point"],
    }


def dump(name, obj):
    p = os.path.join(OUT, "json", name + ".json")
    with open(p, "w") as f:
        json.dump(obj, f, indent=1, default=float)
    print("wrote", p)
