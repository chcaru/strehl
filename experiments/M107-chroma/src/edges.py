"""Edge ROI detection on a raw CFA frame, plus the co-sited-RGB variant of the ESF fit.

An ROI qualifies only if the green planes show ONE straight, high-contrast,
coherent edge. Both the straightness gate and the contrast gate are needed:
Instrument A fits a single erf, so two edges inside the window is a defect of the
stimulus, not of the optics, and it would show up as a per-channel offset.
"""

import numpy as np
from scipy.ndimage import uniform_filter

from common import planes_of, plane_coords, fit_plane_esf, PLANES


def green_of(roi):
    g1, g2 = roi[0::2, 1::2], roi[1::2, 0::2]
    ny, nx = min(g1.shape[0], g2.shape[0]), min(g1.shape[1], g2.shape[1])
    return 0.5 * (g1[:ny, :nx] + g2[:ny, :nx])


def edge_quality(roi):
    """(contrast, coherence, fill) for the green content of a quad-aligned ROI."""
    g = green_of(roi).astype(np.float64)
    gy, gx = np.gradient(g)
    jxx, jyy, jxy = gx * gx, gy * gy, gx * gy
    s = 3
    jxx, jyy, jxy = (uniform_filter(a, s) for a in (jxx, jyy, jxy))
    tr = jxx + jyy
    det = jxx * jyy - jxy * jxy
    disc = np.sqrt(np.maximum(tr * tr - 4 * det, 0.0))
    coh = np.divide(disc, tr, out=np.zeros_like(tr), where=tr > 1e-9)
    mag = np.hypot(gx, gy)
    thr = np.percentile(mag, 90.0)
    m = mag >= thr
    contrast = float(np.percentile(g, 98) - np.percentile(g, 2))
    return contrast, float(np.mean(coh[m])), float(m.mean())


def straightness(roi):
    """RMS deviation of the 90th-percentile gradient ridge from its best-fit line,
    in PLANE px. A single straight edge gives a small number; a hair cluster does not."""
    g = green_of(roi).astype(np.float64)
    gy, gx = np.gradient(g)
    mag = np.hypot(gx, gy)
    thr = np.percentile(mag, 92.0)
    yy, xx = np.nonzero(mag >= thr)
    if xx.size < 40:
        return 1e9
    w = mag[yy, xx] ** 2
    mx, my = (w * xx).sum() / w.sum(), (w * yy).sum() / w.sum()
    dx, dy = xx - mx, yy - my
    cxx = (w * dx * dx).sum() / w.sum()
    cyy = (w * dy * dy).sum() / w.sum()
    cxy = (w * dx * dy).sum() / w.sum()
    tr, det = cxx + cyy, cxx * cyy - cxy * cxy
    lam_min = 0.5 * (tr - np.sqrt(max(tr * tr - 4 * det, 0.0)))
    return float(np.sqrt(max(lam_min, 0.0)))


def find_edge_rois(cfa, size=96, stride=None, top=400, min_contrast=1500.0,
                   min_coh=0.80, max_straight=1.6, margin=64):
    """Scan a full CFA frame for windows holding one straight high-contrast edge.

    `size` is in SENSEL and must be even. Returns a list of dicts sorted by score.
    """
    assert size % 2 == 0
    stride = stride or size
    H, W = cfa.shape
    cands = []
    for y0 in range(margin, H - size - margin, stride):
        if y0 % 2:
            continue
        for x0 in range(margin, W - size - margin, stride):
            if x0 % 2:
                continue
            roi = cfa[y0:y0 + size, x0:x0 + size]
            c, coh, fill = edge_quality(roi)
            if c < min_contrast or coh < min_coh:
                continue
            st = straightness(roi)
            if st > max_straight:
                continue
            cands.append({"x0": x0, "y0": y0, "size": size, "contrast": c,
                          "coherence": coh, "straight": st,
                          "score": c * coh / (0.5 + st)})
    cands.sort(key=lambda d: -d["score"])
    return cands[:top]


def spread_by_radius(cands, cx, cy, nbins=8, per_bin=3, rmax=None):
    """Pick up to `per_bin` ROIs in each of `nbins` radius bins -- so the radius
    sweep measures RADIUS and not whichever part of the subject scored best."""
    if not cands:
        return []
    for c in cands:
        x = c["x0"] + c["size"] / 2.0
        y = c["y0"] + c["size"] / 2.0
        c["radius"] = float(np.hypot(x - cx, y - cy))
        c["rx"] = float(x - cx)
        c["ry"] = float(y - cy)
    rmax = rmax or max(c["radius"] for c in cands)
    out = []
    for b in range(nbins):
        lo, hi = rmax * b / nbins, rmax * (b + 1) / nbins
        sel = [c for c in cands if lo <= c["radius"] < hi][:per_bin]
        out.extend(sel)
    return out


# ------------------------------------------------- co-sited RGB variant (renders)

def esf_rgb(img, x0, y0, size, dmax=12.0):
    """Instrument A on an already-co-sited RGB image (a strehl render).

    Every channel shares one lattice, so there is no co-siting term at all and any
    per-channel offset this reports is optical, demosaic or resampler in origin.
    """
    roi = img[y0:y0 + size, x0:x0 + size, :].astype(np.float64)
    g = roi[:, :, 1]
    gy, gx = np.gradient(g)
    mag = np.hypot(gx, gy)
    thr = np.percentile(mag, 90.0)
    m = mag >= thr
    if m.sum() < 32:
        return None
    ang2 = np.arctan2(2 * gx[m] * gy[m], gx[m] ** 2 - gy[m] ** 2)
    w = mag[m] ** 2
    a = 0.5 * np.arctan2((w * np.sin(ang2)).sum(), (w * np.cos(ang2)).sum())
    n = np.array([np.cos(a), np.sin(a)])
    yy, xx = np.nonzero(m)
    p = np.array([(w * xx).sum() / w.sum(), (w * yy).sum() / w.sum()])
    ys, xs = np.arange(roi.shape[0], dtype=np.float64), np.arange(roi.shape[1], dtype=np.float64)
    X, Y = np.meshgrid(xs, ys)
    out = {}
    for ci, cn in enumerate(("R", "G", "B")):
        f = fit_plane_esf(roi[:, :, ci], X, Y, n, p, dmax=dmax)
        if f is None:
            return None
        out[cn] = f
    return {"planes": out, "normal": [float(n[0]), float(n[1])],
            "point": [float(p[0] + x0), float(p[1] + y0)],
            "contrast": float(np.percentile(g, 98) - np.percentile(g, 2))}
