r"""Paired two-arm gauge for the STREHL_GATE_FLOOR A/B.

Two quantities on the SAME frozen sites, per ORCH's requirement that a rim
number is never quoted without a sharpness number on the same pixels:

  rim()     step-normalised overshoot above the bright plateau, t = +2..+7 px.
            Method re-derived in rimindep.py; shares no code with rimv3/v6,
            both of which I ruled inadmissible (v3 reads +14.85% on a rim-free
            image).
  acuity()  mid-band energy (DoG) over the whole frame. A sharpness number that
            needs no ceiling and no second binary.

Design rules this file is built to, each one earned:

* SITES ARE FROZEN ACROSS ARMS. An earlier version reselected edges per arm;
  blurring removes weak edges, so the two arms were measured over DIFFERENT
  POPULATIONS and the difference carried the population change, not the rim.
* ISOLATION. A max over a textured band is not an overshoot. The profile must
  SETTLE before it may be asked whether it overshot. This excludes most
  high-contrast features on some subjects and the excluded fraction is
  REPORTED, never silently dropped.
* NAN-GUARDED AND TWO-SIDED. `NaN > x` is False, so a NaN reads as "no rim".
  Every acceptance test here is explicit about non-finite input.
* INTEGER-ONLY registration. Sub-pixel resampling adds blur to the very
  quantity being measured.
"""
import numpy as np
from scipy.ndimage import gaussian_filter, gaussian_filter1d

NEAR = 7
MINSTEP = 0.10
PLATEAU = (2, 7)
FLATTEN = 0.06


def luma(a):
    a = a.astype(np.float64) / 65535.0
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def acuity(g, sigma=1.4):
    """Mid-band energy. Exposure-invariant by construction: a DoG kills DC, and
    the normaliser divides by local mean, so a pure gain cancels."""
    band = gaussian_filter(g, sigma) - gaussian_filter(g, 2.0 * sigma)
    m = float(np.mean(np.abs(g))) or 1.0
    return float(np.sqrt(np.mean(band ** 2))) / m


def select(ref, want=6000, seed=0):
    """Edge sites chosen ONCE on a rim-free reference, reused by every arm."""
    rng = np.random.default_rng(seed)
    h, w = ref.shape
    rows = rng.choice(np.arange(200, h - 200), size=min(1400, h - 400),
                      replace=False)
    sites = []
    for y in rows:
        line = gaussian_filter1d(ref[y], 1.0)
        d = np.diff(line)
        ad = np.abs(d)
        for x in np.where(ad[60:w - 60] > MINSTEP * 0.25)[0] + 60:
            v = ad[x]
            far = max(ad[x - NEAR:x - 2].max(initial=0.0),
                      ad[x + 3:x + NEAR + 1].max(initial=0.0))
            if far > 0.5 * v:
                continue
            sites.append((int(y), int(x), 1 if d[x] > 0 else -1))
            if len(sites) >= want:
                break
        if len(sites) >= want:
            break
    return sites


def profiles(g, sites):
    """Measure frozen sites on whatever image is supplied.

    Returns (profiles, n_offered, n_isolated) so the caller can report the
    fraction of features the axis can actually speak to."""
    out = []
    offered = 0
    for y, x, sgn in sites:
        line = gaussian_filter1d(g[y], 1.0)
        if sgn > 0:
            dark = line[x - NEAR:x - 1].mean()
            seg = line[x + 2:x + NEAR + 2]
        else:
            dark = line[x + 3:x + NEAR + 2].mean()
            seg = line[x - NEAR:x - 1][::-1]
        if seg.size < NEAR - 1:
            continue
        bright = seg[-3:].mean()
        step = bright - dark
        if not np.isfinite(step) or step < MINSTEP:
            continue
        offered += 1
        prof = (seg[:NEAR - 1] - dark) / step
        if prof.size < 4 or not np.all(np.isfinite(prof)):
            continue
        if np.abs(np.diff(prof[-3:])).max() > FLATTEN:
            continue
        out.append(prof)
    p = np.asarray(out) if out else np.zeros((0, NEAR - 1))
    return p, offered, len(out)


def rim(g, sites):
    """Median step-normalised overshoot. NaN when no site survives isolation --
    which the caller must treat as REFUSED, never as a pass."""
    p, offered, kept = profiles(g, sites)
    if kept == 0:
        return float("nan"), offered, 0
    lo, hi = PLATEAU
    peak = p[:, max(lo - 2, 0):hi - 1].max(axis=1)
    return float(np.median(peak) - 1.0), offered, kept


def int_shift(a, b, search=6):
    """Integer-only alignment of b onto a. Sub-pixel would add blur."""
    h, w = a.shape
    cy, cx = h // 2, w // 2
    pa = a[cy - 256:cy + 256, cx - 256:cx + 256]
    best, bs = None, (0, 0)
    for dy in range(-search, search + 1):
        for dx in range(-search, search + 1):
            pb = b[cy - 256 + dy:cy + 256 + dy, cx - 256 + dx:cx + 256 + dx]
            if pb.shape != pa.shape:
                continue
            e = float(np.mean((pa - pb) ** 2))
            if best is None or e < best:
                best, bs = e, (dy, dx)
    return bs, best
