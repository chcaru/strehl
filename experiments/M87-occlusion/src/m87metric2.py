"""M87 metric v2 -- local edge-normal overshoot.

Metric v1 (PREREGISTRATION section 2: radial distance profile against a
far-field linear baseline) FAILED its own registered G1 bar on the shipped
render: H / H_shift = 1.71-1.76x against a required 4x.  Section 2.1 named the
failure direction correctly -- the far-field baseline assumes the background is
one homogeneous surface at a single level, and in `bee-3-cpl` it is not: the
card carries a large-scale illumination gradient, and the perimeter of the
subject samples wildly different parts of it.  Averaging over the whole
perimeter at fixed distance therefore mixes background levels that differ by
far more than the halo.

v2 removes that assumption.  A halo is, definitionally, a LOCAL OVERSHOOT: as
you walk outward from an edge, the value rises past the level it eventually
settles at, then comes back down.  Measure exactly that, one edge point at a
time, with each profile carrying its own local asymptote:

  for each boundary sample j with outward unit normal n_j at point p_j
      s_j(d) = image( p_j + d n_j )                d = 0 .. D_MAX
      b_j    = median_{d in D_BASE} s_j(d)         local asymptote
      q_j(d) = s_j(d) / b_j                        local normalisation
      o_j    = max_{d in D_PEAK} q_j(d)  -  1      local overshoot

  O = median_j o_j

O > 0  <=>  the value overshoots its own local asymptote on the way out of the
edge, i.e. a bright halo.  O ~ 0 <=> monotone approach, i.e. a clean edge.
O < 0 <=> undershoot (a dark halo).

Why this is the right shape of instrument here:

  * it is EDGE-REFERENCED, which SYNTHESIS fact 64 requires of any halo metric
    (per-pixel ROI averages are structurally blind to it);
  * every profile is divided by its OWN far value, so a large-scale
    illumination gradient across the card cancels to first order;
  * it is defined identically for a merge and for a single frame, so the
    single-frame control C2 is an exactly PAIRED comparison on the same
    boundary points and the same normals;
  * the null is a real physical statement, not a fitted baseline: a defocused
    occluding edge in a single exposure has a MONOTONE edge-spread profile, so
    it must score ~0.

Failure direction of v2, stated before use: if the true background is not
locally flat over D_MAX px along the normal -- e.g. another subject part, or a
strong background texture just outside the edge -- b_j is wrong and o_j picks up
scene content.  The controls below are what catch that: the same statistic on a
mask translated into empty background (C1) and on a disc planted in flat
background (C3) must both return ~0.
"""

import numpy as np
from scipy import ndimage as ndi

D_MAX = 64
D_PEAK = (4, 32)
D_BASE = (48, 64)
BOUNDARY_STEP = 1
NORMAL_SMOOTH = 4.0
MIN_PROFILES = 200


def boundary_normals(mask, roi=None, step=BOUNDARY_STEP, smooth=NORMAL_SMOOTH):
    """Outward unit normals on the outer boundary of `mask`.

    The normal is the gradient of the (smoothed) exterior distance transform,
    which points away from the mask by construction, so 'outward' needs no
    orientation bookkeeping.
    """
    dist = ndi.distance_transform_edt(~mask).astype(np.float32)
    ds = ndi.gaussian_filter(dist, smooth)
    gy, gx = np.gradient(ds)
    mag = np.hypot(gy, gx)

    # boundary = background pixels adjacent to the mask
    edge = (~mask) & ndi.binary_dilation(mask, ndi.generate_binary_structure(2, 2))
    if roi is not None:
        y0, y1, x0, x1 = roi
        keep = np.zeros(mask.shape, bool)
        keep[y0:y1, x0:x1] = True
        edge &= keep
    ys, xs = np.nonzero(edge)
    if step > 1:
        ys, xs = ys[::step], xs[::step]
    ok = mag[ys, xs] > 1e-3
    ys, xs = ys[ok], xs[ok]
    ny = gy[ys, xs] / mag[ys, xs]
    nx = gx[ys, xs] / mag[ys, xs]
    return np.stack([ys, xs], 1).astype(np.float32), np.stack([ny, nx], 1)


def _bilinear(img, y, x):
    h, w = img.shape
    y = np.clip(y, 0, h - 1.001)
    x = np.clip(x, 0, w - 1.001)
    y0 = np.floor(y).astype(np.int32)
    x0 = np.floor(x).astype(np.int32)
    fy = (y - y0)[..., None] if False else (y - y0)
    fx = x - x0
    v = (img[y0, x0] * (1 - fy) * (1 - fx)
         + img[y0 + 1, x0] * fy * (1 - fx)
         + img[y0, x0 + 1] * (1 - fy) * fx
         + img[y0 + 1, x0 + 1] * fy * fx)
    return v


def sample_profiles(img, pts, nrm, d_max=D_MAX):
    d = np.arange(d_max + 1, dtype=np.float32)[None, :]
    y = pts[:, 0][:, None] + nrm[:, 0][:, None] * d
    x = pts[:, 1][:, None] + nrm[:, 1][:, None] * d
    return _bilinear(np.asarray(img, np.float32), y, x), y, x


def valid_profiles(mask, pts, nrm, d_max=D_MAX):
    """Drop profiles that re-enter the mask or leave the frame."""
    d = np.arange(d_max + 1, dtype=np.float32)[None, :]
    y = pts[:, 0][:, None] + nrm[:, 0][:, None] * d
    x = pts[:, 1][:, None] + nrm[:, 1][:, None] * d
    h, w = mask.shape
    inside = (y >= 0) & (y <= h - 1.01) & (x >= 0) & (x <= w - 1.01)
    yi = np.clip(np.rint(y), 0, h - 1).astype(np.int32)
    xi = np.clip(np.rint(x), 0, w - 1).astype(np.int32)
    hits = mask[yi, xi]
    hits[:, :2] = False  # d=0,1 may legitimately touch the boundary
    return inside.all(1) & (~hits.any(1))


def overshoot(prof, d_peak=D_PEAK, d_base=D_BASE):
    """Per-profile overshoot o_j and the normalised profiles q_j(d)."""
    b = np.median(prof[:, d_base[0]:d_base[1] + 1], axis=1)
    good = b > 1.0
    q = prof[good] / b[good][:, None]
    o = q[:, d_peak[0]:d_peak[1] + 1].max(axis=1) - 1.0
    dstar = q[:, d_peak[0]:d_peak[1] + 1].argmax(axis=1) + d_peak[0]
    return o, q, dstar, good


def boot_ci(x, n=2000, seed=87, q=(2.5, 97.5)):
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(x), size=(n, len(x)))
    meds = np.median(np.asarray(x)[idx], axis=1)
    return float(np.percentile(meds, q[0])), float(np.percentile(meds, q[1]))


def score(img, mask, pts, nrm, valid, d_peak=D_PEAK, d_base=D_BASE, d_max=D_MAX):
    prof, _, _ = sample_profiles(img, pts[valid], nrm[valid], d_max)
    o, q, dstar, good = overshoot(prof, d_peak, d_base)
    if len(o) < MIN_PROFILES:
        return None
    lo, hi = boot_ci(o)
    return {
        "O": float(np.median(o)),
        "O_ci": [lo, hi],
        "O_mean": float(o.mean()),
        "O_iqr": [float(np.percentile(o, 25)), float(np.percentile(o, 75))],
        "frac_pos": float((o > 0).mean()),
        "d_star": float(np.median(dstar)),
        "n": int(len(o)),
        "q_mean": q.mean(axis=0),
        "o": o,
    }
