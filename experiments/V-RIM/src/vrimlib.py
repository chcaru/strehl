"""V-RIM independent profiler. Written from scratch to re-derive ORCH-veiling
section 12 without reusing rimprofile.py.

Deliberate differences from the instrument under test:

  mask       Otsu on luminance, then the BACKDROP is defined as the largest
             border-touching component of the backdrop-polarity map, and the
             subject is the filled complement. ORCH assumed the subject is the
             dark side and thresholded at the midpoint of p5 and p95.
  polarity   decided from the image border, not assumed.
  channel    green by default. Green is sampled twice per Bayer quad, so it is
             the channel a demosaic interpolates least. ORCH used the
             unweighted RGB mean.
  bins       1 px out to 60 px. ORCH's first bin was 4 px wide.
  reference  reported four ways, and the whole profile is printed to the
             largest available distance so the plateau is visible.
  controls   two, neither of which ORCH has:
               PLACEBO  the same statistic around a synthetic disc dropped in
                        empty backdrop. Any dip it shows is illumination, not
                        the subject.
               NULLPROM the same ring-prominence statistic computed on a
                        subject-free stretch of the same backdrop, which is the
                        per-subject noise floor the ring must beat.
  zero point mask dilated and eroded by +/-2, +/-5, +/-10 px and the profile
             recomputed, because the threshold crossing sits somewhere inside
             the edge transition and every distance inherits that offset.

Nothing here reads rimprofile.py's output.
"""
import json
import sys
from pathlib import Path

import numpy as np
import tifffile
from scipy import ndimage

try:
    from skimage.filters import threshold_otsu
except Exception:  # pragma: no cover
    threshold_otsu = None


def otsu(x):
    if threshold_otsu is not None:
        return float(threshold_otsu(x[::4, ::4]))
    h, e = np.histogram(x[::4, ::4], bins=512)
    c = 0.5 * (e[:-1] + e[1:])
    w0 = np.cumsum(h)
    w1 = w0[-1] - w0
    m0 = np.cumsum(h * c) / np.maximum(w0, 1)
    m1 = (np.cumsum((h * c)[::-1])[::-1] - h * c + 1e-9) / np.maximum(w1, 1)
    v = w0 * w1 * (m0 - m1) ** 2
    return float(c[int(np.argmax(v))])


def load_lum(path, channel="G"):
    img = tifffile.imread(str(path))
    assert img.dtype == np.uint16, f"expected uint16, got {img.dtype}"
    assert img.ndim == 3 and img.shape[2] == 3, f"expected HxWx3, got {img.shape}"
    a = img.astype(np.float32)
    ch = {"R": a[:, :, 0], "G": a[:, :, 1], "B": a[:, :, 2],
          "mean": a.mean(axis=2)}[channel]
    return img.shape, ch


def border_mask(shape, frac=0.01):
    h, w = shape
    b = np.zeros(shape, bool)
    t = max(2, int(round(frac * min(h, w))))
    b[:t, :] = b[-t:, :] = b[:, :t] = b[:, -t:] = True
    return b


def segment(lum):
    """Return (subject_bool, backdrop_bool, diagnostics dict)."""
    t = otsu(lum)
    bright = lum > t
    bm = border_mask(lum.shape)
    frac_bright_border = float(bright[bm].mean())
    backdrop_is_bright = frac_bright_border >= 0.5
    cand = bright if backdrop_is_bright else ~bright

    lab, n = ndimage.label(cand)
    if n == 0:
        raise RuntimeError("no backdrop candidate component")
    border_labels = np.unique(lab[bm])
    border_labels = border_labels[border_labels > 0]
    if border_labels.size == 0:
        sizes = ndimage.sum(cand, lab, range(1, n + 1))
        pick = 1 + int(np.argmax(sizes))
    else:
        sizes = ndimage.sum(cand, lab, border_labels)
        pick = int(border_labels[int(np.argmax(sizes))])
    backdrop = lab == pick

    # subject: everything the backdrop is not, holes filled, largest component
    notb = ~backdrop
    notb = ndimage.binary_fill_holes(notb)
    lab2, n2 = ndimage.label(notb)
    if n2 == 0:
        raise RuntimeError("no subject component")
    sizes2 = ndimage.sum(notb, lab2, range(1, n2 + 1))
    subject = lab2 == (1 + int(np.argmax(sizes2)))

    diag = dict(otsu=t, frac_bright_border=frac_bright_border,
                backdrop_is_bright=bool(backdrop_is_bright),
                n_backdrop_components=int(n),
                backdrop_frac=float(backdrop.mean()),
                subject_frac=float(subject.mean()),
                n_notbackdrop_components=int(n2),
                subject_largest_share=float(sizes2.max() / sizes2.sum()))
    return subject, backdrop, diag


def signed_distance(subject):
    d_out = ndimage.distance_transform_edt(~subject).astype(np.float32)
    d_in = ndimage.distance_transform_edt(subject).astype(np.float32)
    return d_out - d_in


EDGES = (list(range(0, 61)) + [65, 70, 75, 80, 90, 100, 110, 125, 150, 175,
                               200, 250, 300, 350, 400, 500, 600, 700, 800,
                               1000, 1200, 1400, 1700, 2000, 2500, 3000])


def profile(lum, signed, valid, edges=EDGES, minpix=200):
    rows = []
    for i in range(len(edges) - 1):
        m = valid & (signed >= edges[i]) & (signed < edges[i + 1])
        c = int(m.sum())
        if c < minpix:
            continue
        v = lum[m]
        rows.append(dict(lo=edges[i], hi=edges[i + 1],
                         d=0.5 * (edges[i] + edges[i + 1]), n=c,
                         med=float(np.median(v)),
                         q25=float(np.percentile(v, 25)),
                         q75=float(np.percentile(v, 75))))
    return rows


def prominence(rows, ref, dmin=0.0, dmax=1e9):
    """Largest interior local maximum, scored by height above the lowest point
    between it and the outer end of the window. Stated once, applied to the
    real profile and to the null identically."""
    sel = [r for r in rows if dmin <= r["d"] <= dmax]
    if len(sel) < 3:
        return None
    v = np.array([r["med"] for r in sel])
    d = np.array([r["d"] for r in sel])
    best = None
    for i in range(1, len(v) - 1):
        if v[i] >= v[i - 1] and v[i] > v[i + 1]:
            trough = float(v[i + 1:].min())
            p = float(v[i] - trough)
            if best is None or p > best[2]:
                best = (float(d[i]), float(v[i]), p)
    if best is None:
        return None
    return dict(d=best[0], val=best[1], prom=best[2], prom_frac=best[2] / ref)


def place_disc(subject, backdrop, signed):
    """Drop a synthetic disc into empty backdrop, as far from the subject as it
    can get. Its profile is the illumination control."""
    far = signed.copy()
    far[~backdrop] = -1
    idx = int(np.argmax(far))
    cy, cx = np.unravel_index(idx, far.shape)
    room = float(far[cy, cx])
    r = float(min(200.0, max(20.0, room / 3.0)))
    yy, xx = np.ogrid[:subject.shape[0], :subject.shape[1]]
    disc = (yy - cy) ** 2 + (xx - cx) ** 2 <= r * r
    return disc, dict(cy=int(cy), cx=int(cx), radius=r, room=room)
