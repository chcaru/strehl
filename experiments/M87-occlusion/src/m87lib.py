"""M87 shared library: the frozen halo metric, the merge, and the loaders.

The merge is a second implementation of the shipped one, transcribed from
`experiments/m52-gate-cluster/src/03-fact324-n-eff-independent.py`, which M52
measured as agreeing with the shipped binary to <= 0.09% on all seven stacks
(SYNTHESIS fact 324's re-derivation; see `merge_cmd.rs` doc comment on
`target_n_eff`).

    luma   = 0.5 * (max(G1-black,0) + max(G2-black,0))          plane.rs
    grad   = 0.125 * hypot(Sobel_x, Sobel_y), replicate border   focus.rs
    focus  = clamped_box(grad, 13) / green_luma_sigma(luma)      focus.rs + noise.rs
    reg    = clamped_box(focus, 8)                               merge.rs
    best   = max over frames                                     merge.rs FocusStats
    admit  = { k : best - reg_k <= t * sqrt(2) * FOCUS_NOISE_SD } merge.rs Estimator

RULE 32: `raw_image_visible` is a VIEW into LibRaw's buffer. Every read copies
inside the `with`.

The halo metric `H` is frozen in `experiments/M87-occlusion/PREREGISTRATION.md`
section 2 and is implemented here once, so that every arm uses the same code.
"""

from __future__ import annotations

import pathlib

import numpy as np
import rawpy
from scipy.ndimage import (
    binary_closing,
    binary_opening,
    distance_transform_edt,
    label,
    uniform_filter,
)

# ---------------------------------------------------------------- constants
FOCUS_NOISE_SD = 0.015214
WINDOW_RADIUS = 13
REGULARISER_RADIUS = 8
SIGMA_EPS = 1e-3
BLACK = 512.0
WHITE = 16383.0
GAIN_DIVISOR = 436.8
BASE_ISO = 100.0
SECOND_BASE_ISO = 400.0
RN_LOW = 4.20
RN_HIGH = 1.47
SQRT2 = float(np.sqrt(2.0))

# frozen metric constants -- PREREGISTRATION section 2
D_MAX = 96
D_FAR = (48, 96)
D_NEAR = (1, 24)
MIN_BIN = 200
MASK_DISC_R = 3
MASK_MIN_COMPONENT = 2000
SHIFT_OFFSET = (512, 512)

ROIS = {
    "ROI_LEG": (1200, 1900, 300, 1400),
    "ROI_BODY": (200, 900, 1500, 2600),
    "ROI_FLAT": (1300, 2300, 0, 180),
}


# ---------------------------------------------------------------- operators
_COUNT_CACHE: dict = {}


def _counts(n, r):
    i = np.arange(n)
    return (np.minimum(i + r, n - 1) - np.maximum(i - r, 0) + 1).astype(np.float64)


def clamped_box(a, r):
    """Mean over a (2r+1)^2 window intersected with the plane -- boxfilter.rs."""
    n = 2 * r + 1
    s = uniform_filter(a, size=n, mode="constant", cval=0.0) * float(n * n)
    key = (a.shape, r)
    d = _COUNT_CACHE.get(key)
    if d is None:
        d = _counts(a.shape[0], r)[:, None] * _counts(a.shape[1], r)[None, :]
        _COUNT_CACHE[key] = d
    return s / d


def sobel_mag(a):
    p = np.pad(a, 1, mode="edge")

    def at(dy, dx):
        return p[1 + dy : 1 + dy + a.shape[0], 1 + dx : 1 + dx + a.shape[1]]

    gx = at(-1, 1) + 2.0 * at(0, 1) + at(1, 1) - at(-1, -1) - 2.0 * at(0, -1) - at(1, -1)
    gy = at(1, -1) + 2.0 * at(1, 0) + at(1, 1) - at(-1, -1) - 2.0 * at(-1, 0) - at(-1, 1)
    return np.hypot(0.125 * gx, 0.125 * gy)


def green_luma_sigma(luma, iso):
    g = max(iso, BASE_ISO) / GAIN_DIVISOR
    rn = RN_HIGH if iso >= SECOND_BASE_ISO else RN_LOW
    read_dn = rn * g
    var = g * np.maximum(luma, 0.0) + read_dn * read_dn
    return np.sqrt(0.25 * (var + var))


def regularised_field(luma, iso):
    f = clamped_box(sobel_mag(luma), WINDOW_RADIUS)
    f /= np.maximum(green_luma_sigma(luma, iso), SIGMA_EPS)
    return clamped_box(f, REGULARISER_RADIUS).astype(np.float32)


# ---------------------------------------------------------------- RAW input
def frames(d):
    return sorted(str(p) for p in pathlib.Path(d).iterdir() if p.suffix.upper() == ".ARW")


def read_planes(path, box=None):
    """R, G1, G2, B as f32, black NOT subtracted, on the binned grid.

    `box` is (y0, y1, x0, x1) in BINNED coordinates. Copies inside the `with`
    (rule 32) and slices the copy, never the view.
    """
    with rawpy.imread(path) as rr:
        v = rr.raw_image_visible
        h = (v.shape[0] // 2) * 2
        w = (v.shape[1] // 2) * 2
        if box is None:
            y0, y1, x0, x1 = 0, h // 2, 0, w // 2
        else:
            y0, y1, x0, x1 = box
        r = np.array(v[2 * y0 : 2 * y1 : 2, 2 * x0 : 2 * x1 : 2], dtype=np.float32)
        g1 = np.array(v[2 * y0 : 2 * y1 : 2, 2 * x0 + 1 : 2 * x1 : 2], dtype=np.float32)
        g2 = np.array(v[2 * y0 + 1 : 2 * y1 : 2, 2 * x0 : 2 * x1 : 2], dtype=np.float32)
        b = np.array(v[2 * y0 + 1 : 2 * y1 : 2, 2 * x0 + 1 : 2 * x1 : 2], dtype=np.float32)
    return r, g1, g2, b


def luma_of(path, box=None):
    _, g1, g2, _ = read_planes(path, box)
    return 0.5 * (np.maximum(g1 - BLACK, 0.0) + np.maximum(g2 - BLACK, 0.0))


def binned_grid_shape(path):
    with rawpy.imread(path) as rr:
        v = rr.raw_image_visible
        return (v.shape[0] // 2, v.shape[1] // 2)


# ---------------------------------------------------------------- the metric
def otsu(a, bins=512):
    """Standard two-class threshold. No peak-finding heuristic, no free knob."""
    hist, edges = np.histogram(a, bins=bins, range=(float(a.min()), float(a.max())))
    c = 0.5 * (edges[:-1] + edges[1:])
    w0 = np.cumsum(hist)
    w1 = w0[-1] - w0
    cw = np.cumsum(hist * c)
    mu0 = cw / np.maximum(w0, 1)
    mu1 = ((hist * c).sum() - cw) / np.maximum(w1, 1)
    return float(c[int(np.argmax(w0 * w1 * (mu0 - mu1) ** 2))])


def foreground_mask(luma, hist_roi=None, tau=None):
    """PREREGISTRATION section 2 step 1, with a DISCLOSED deviation.

    Registered rule: "the midpoint between the two dominant modes of the ROI
    luma histogram (128 bins, modes located by the two largest peaks after a
    3-bin box smooth)". Measured on `bee3-g0.tif` that rule returns tau = 33540,
    a foreground fraction of 0.698, and puts **46% of the registered
    background-only ROI_FLAT inside the mask** -- because the *background* of
    this capture is itself bimodal (two card/surface modes near 30 800 and
    37 800 DN), so both "dominant modes" are background and their midpoint cuts
    the background in half.

    Replaced by **Otsu**, which is the standard two-class rule, has no
    peak-selection heuristic and no tunable constant. It returns tau = 23937,
    foreground fraction 0.3654, and **ROI_FLAT foreground fraction 0.00000**.
    The deviation and both sets of numbers are disclosed in the report.
    """
    src = luma if hist_roi is None else luma[hist_roi[0] : hist_roi[1], hist_roi[2] : hist_roi[3]]
    if tau is None:
        tau = otsu(src)

    m = luma < tau
    disc = _disc(MASK_DISC_R)
    m = binary_closing(m, structure=disc)
    m = binary_opening(m, structure=disc)
    lab, n = label(m)
    if n:
        sizes = np.bincount(lab.ravel())
        sizes[0] = 0
        keep = np.isin(lab, np.nonzero(sizes >= MASK_MIN_COMPONENT)[0])
        m = keep
    return m, tau


def _disc(r):
    y, x = np.ogrid[-r : r + 1, -r : r + 1]
    return (y * y + x * x) <= r * r


def band_profile(value, mask, roi, d_max=D_MAX, min_bin=MIN_BIN):
    """P(d): median of `value` over background pixels at distance d, inside roi."""
    dist = distance_transform_edt(~mask)
    y0, y1, x0, x1 = roi
    d = dist[y0:y1, x0:x1]
    v = value[y0:y1, x0:x1]
    bg = ~mask[y0:y1, x0:x1]
    dr = np.rint(d).astype(np.int32)
    prof = np.full(d_max + 1, np.nan)
    cnt = np.zeros(d_max + 1, np.int64)
    sel = bg & (dr >= 1) & (dr <= d_max)
    ds = dr[sel]
    vs = v[sel]
    order = np.argsort(ds, kind="stable")
    ds = ds[order]
    vs = vs[order]
    edges = np.searchsorted(ds, np.arange(1, d_max + 2))
    for i in range(d_max):
        a, b = edges[i], edges[i + 1]
        cnt[i + 1] = b - a
        if b - a >= min_bin:
            prof[i + 1] = np.median(vs[a:b])
    return prof, cnt


def halo_from_profile(prof, d_far=D_FAR, d_near=D_NEAR):
    """PREREGISTRATION section 2 steps 4-7. Returns dict with H, H_signed, W, E."""
    d = np.arange(len(prof))
    far = (d >= d_far[0]) & (d <= d_far[1]) & np.isfinite(prof)
    if far.sum() < 8:
        return None
    a, b = np.polyfit(d[far], prof[far], 1)
    base = a * d + b
    e = prof - base
    near = (d >= d_near[0]) & (d <= d_near[1]) & np.isfinite(e)
    if near.sum() == 0:
        return None
    idx = np.nanargmax(np.where(near, np.abs(e), np.nan))
    h = float(abs(e[idx]))
    w = None
    for k in range(int(idx) + 1, len(e)):
        if np.isfinite(e[k]) and abs(e[k]) < h / np.e:
            w = int(k)
            break
    return {
        "H": h,
        "H_signed": float(e[idx]),
        "d_star": int(idx),
        "W": w,
        "baseline0": float(base[0]),
        "H_pct": 100.0 * h / max(float(base[0]), 1e-9),
        "E": e,
        "P": prof,
        "baseline": base,
    }


def shifted_mask(mask, offset=SHIFT_OFFSET):
    """C1: translate the mask, preserving every spatial statistic of it."""
    out = np.zeros_like(mask)
    dy, dx = offset
    h, w = mask.shape
    out[dy:h, dx:w] = mask[0 : h - dy, 0 : w - dx]
    return out


def measure(value, mask, roi, tag=""):
    prof, cnt = band_profile(value, mask, roi)
    r = halo_from_profile(prof)
    if r is not None:
        r["tag"] = tag
        r["counts"] = cnt
    return r


# ---------------------------------------------------------------- the merge
def merge_stack(files, iso, box, gates, want_planes=("G",), progress=None):
    """Two-pass noise-gated merge on a binned box. Returns dict per gate.

    Pass one caches the binned luma (uint16-safe f32) and computes `best`.
    Pass two admits and averages. `gate = 0.0` means pure argmax selection.
    """
    n = len(files)
    h = box[1] - box[0]
    w = box[3] - box[2]
    lumas = np.empty((n, h, w), np.float32)
    fields = np.empty((n, h, w), np.float32)
    planes = {}
    for k, p in enumerate(files):
        r, g1, g2, b = read_planes(p, box)
        lm = 0.5 * (np.maximum(g1 - BLACK, 0.0) + np.maximum(g2 - BLACK, 0.0))
        lumas[k] = lm
        fields[k] = regularised_field(lm.astype(np.float64), iso)
        if "R" in want_planes:
            planes.setdefault("R", np.empty((n, h, w), np.float32))[k] = r - BLACK
        if "B" in want_planes:
            planes.setdefault("B", np.empty((n, h, w), np.float32))[k] = b - BLACK
        if progress and k % 50 == 0:
            progress(k, n)
    planes["G"] = lumas
    best = fields.max(axis=0)
    argbest = fields.argmax(axis=0).astype(np.int32)

    out = {"best": best, "argbest": argbest, "fields": fields, "planes": planes}
    for t in gates:
        if t == 0.0:
            res = {pl: np.take_along_axis(arr, argbest[None], 0)[0].copy()
                   for pl, arr in planes.items()}
            res["n_eff"] = np.ones((h, w), np.float32)
        else:
            tol = np.float32(t) * np.float32(SQRT2) * np.float32(FOCUS_NOISE_SD)
            adm = (best[None] - fields) <= tol
            cnt = adm.sum(axis=0).astype(np.float32)
            res = {}
            for pl, arr in planes.items():
                res[pl] = (np.where(adm, arr, 0.0).sum(axis=0) / np.maximum(cnt, 1)).astype(
                    np.float32
                )
            res["n_eff"] = cnt
        out[f"gate{t}"] = res
    return out
