r"""Paired rim/acuity core for an arbitrary two-file A/B. No SHIP-V4 dependency.

WHY THIS FILE EXISTS. rimaxis.py and rimindep.py are both hardcoded to the
SHIP-V4 seal directory and its `--SHIP-V4.tiff` suffix. ORCH asked for the rim
axis on a pair of files that are not in that seal, so the SELECTION and
MEASUREMENT core is restated here against two explicit paths. What is NOT
changed: frozen sites, the isolation rule, integer-only registration, and
two-sided NaN guards.

THE TRAP THIS FILE IS BUILT TO CATCH, in ORCH's words: rim may move "only by
softening the edge itself rather than the aura beside it". A step-normalised
overshoot CANNOT distinguish those on its own -- blurring an image lowers it,
and lowering it is what an improvement also looks like. So every rim number
here is emitted with a RISE number measured on THE SAME PROFILE at THE SAME
SITE in the same pass:

    rim   = max(prof[t=+2..+7]) - 1        the aura BESIDE the edge
    rise  = t(0.9) - t(0.1)                the sharpness OF the edge

An arm that lowers rim while holding rise is removing an aura.
An arm that lowers rim by raising rise is softening, and must be reported as
softening no matter how good the rim number looks.

Both are computed from one normalised profile per site, so they cannot drift
onto different populations -- the defect that made an earlier version read its
null larger than its master.
"""
import numpy as np
from scipy.ndimage import gaussian_filter, gaussian_filter1d

NEAR = 9
MINSTEP = 0.10
PLATEAU = (2, 7)
FLATTEN = 0.06
PRESMOOTH = 1.0


def luma(a):
    a = a.astype(np.float64) / 65535.0
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def select(ref, want=6000, seed=0):
    """Edge sites chosen ONCE on a rim-free reference and reused by every arm.

    Reselecting per arm measures two arms over two populations and the
    difference then carries the population change, not the rim."""
    rng = np.random.default_rng(seed)
    h, w = ref.shape
    rows = rng.choice(np.arange(200, h - 200), size=min(3000, h - 400),
                      replace=False)
    sites = []
    for y in rows:
        line = gaussian_filter1d(ref[y], PRESMOOTH)
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


def _full_profile(line, x, sgn):
    """Normalised profile on a fixed grid t = -NEAR .. +NEAR+1.

    Oriented dark-to-bright for both edge signs by mirroring about the step, so
    a dark-side and a bright-side edge contribute the same shape and the median
    is not a mixture of two conventions."""
    if sgn > 0:
        idx = np.arange(x - NEAR, x + NEAR + 2)
    else:
        idx = np.arange(x + NEAR, x - NEAR - 2, -1)
    if idx.min() < 0 or idx.max() >= line.size:
        return None
    v = line[idx]
    dark = v[:NEAR - 2].mean()
    bright = v[-3:].mean()
    step = bright - dark
    if not np.isfinite(step) or step < MINSTEP:
        return None
    p = (v - dark) / step
    if not np.all(np.isfinite(p)):
        return None
    return p


def measure(g, sites, keep=None):
    """Measure rim and rise at frozen sites. Returns a dict.

    THE DEFECT THIS SIGNATURE EXISTS TO PREVENT, found by commissioning and not
    by inspection. Freezing the SITE LIST is not enough. The isolation rule --
    the profile must settle before it may be asked whether it overshot -- was
    being evaluated on each arm's OWN profile, so a blurred arm settled more
    often and was admitted more often: 182 sites kept on the control against 296
    on a blur of the same image, an 63% larger population. The difference
    between two such arms carries the population change, not the rim change.
    That is the same defect that once made a null read larger than its master.

    So `keep` freezes the ISOLATION SET as well. It is derived once on the
    control arm and every other arm is measured at exactly those indices,
    whether or not they would have qualified on their own. Sites that cannot
    yield a profile at all on some arm are counted as `dropouts` and reported --
    a silent dropout is a population change wearing a different hat.
    """
    rims, rises, slopes = [], [], []
    offered, dropouts = 0, 0
    kept_idx = []
    rows = {}
    want = None if keep is None else set(keep)
    for i, (y, x, sgn) in enumerate(sites):
        if want is not None and i not in want:
            continue
        if y not in rows:
            rows[y] = gaussian_filter1d(g[y], PRESMOOTH)
        p = _full_profile(rows[y], x, sgn)
        if p is None:
            if want is not None:
                dropouts += 1
            continue
        offered += 1
        if want is None:
            # ISOLATION, evaluated ONLY on the control arm.
            if np.abs(np.diff(p[-3:])).max() > FLATTEN:
                continue
        lo, hi = PLATEAU
        seg = p[NEAR + lo:NEAR + hi + 1]
        if seg.size == 0:
            continue
        kept_idx.append(i)
        rims.append(float(seg.max()) - 1.0)
        r = _rise(p)
        if r is not None:
            rises.append(r)
        s = _rise_slope(p)
        if s is not None:
            slopes.append(s)
    if not rims:
        return {"rim": float("nan"), "rise": float("nan"), "rise_c": float("nan"),
                "n": 0, "offered": offered, "dropouts": dropouts, "keep": []}
    return {"rim": float(np.median(rims)),
            "rise": float(np.median(rises)) if rises else float("nan"),
            "rise_c": float(np.median(slopes)) if slopes else float("nan"),
            "n": len(rims), "offered": offered, "dropouts": dropouts,
            "keep": kept_idx}


def _rise(p):
    """10-90 rise distance in pixels, linearly interpolated, on the SAME
    normalised profile the rim came from."""
    t = np.arange(p.size, dtype=np.float64)
    a = _cross(t, p, 0.1)
    b = _cross(t, p, 0.9)
    if a is None or b is None or not np.isfinite(a) or not np.isfinite(b):
        return None
    if b <= a:
        return None
    return float(b - a)


def _rise_slope(p):
    """10-90-equivalent rise derived from the SLOPE AT THE EDGE CENTRE.

    WHY THIS EXISTS, and it is not a refinement -- it is a correction to a
    defect the commissioning found in `_rise`. A planted aura of amplitude 0.15
    drove the 10-90 rise from 3.62 px to 3.18 px on a synthetic edge whose
    blur was IDENTICAL, because elevating t=+2..+7 makes the profile reach 0.9
    earlier. Measured coupling is about -4 px of rise per unit of rim.

    That coupling runs the WRONG WAY for this experiment. The arm under test is
    expected to REDUCE rim, and a reduction would push the 10-90 rise UP with no
    blur whatever -- a genuine de-ringing would be reported as softening.

    The 0.5 crossing sits at the edge centre, t ~ 0, which is outside the aura
    band on both sides. For a gaussian edge the peak slope is
    1/(sigma*sqrt(2pi)) and the 10-90 rise is 2*1.2816*sigma, so
    rise = 1.0225/slope. Commissioned to be flat under the same plant that
    breaks `_rise`.
    """
    t = np.arange(p.size, dtype=np.float64)
    c = _cross(t, p, 0.5)
    if c is None:
        return None
    d = np.gradient(p)
    i = int(round(c))
    lo, hi = max(i - 2, 0), min(i + 3, p.size)
    if hi <= lo:
        return None
    s = float(np.max(d[lo:hi]))
    if not np.isfinite(s) or s <= 1e-6:
        return None
    return 1.0225 / s


def _cross(t, p, level):
    """First upward crossing of `level`, interpolated. None if it never
    crosses -- a degenerate profile must not silently contribute a 0."""
    w = np.where(p >= level)[0]
    if w.size == 0 or w[0] == 0:
        return None
    i = w[0]
    y0, y1 = p[i - 1], p[i]
    if y1 == y0:
        return float(t[i])
    return float(t[i - 1] + (level - y0) / (y1 - y0))


def acuity(g, sigma=1.4):
    """Mid-band energy, exposure-invariant (DoG kills DC, divide by local mean).

    Quoted only alongside the structure split -- Part 15 measured a global
    metric reading -22.42% where detail moved -1.21%."""
    band = gaussian_filter(g, sigma) - gaussian_filter(g, 2.0 * sigma)
    m = float(np.mean(np.abs(g))) or 1.0
    return float(np.sqrt(np.mean(band ** 2))) / m


def int_shift(a, b, search=6):
    """Integer-only alignment. Sub-pixel resampling adds blur to the very
    quantity being measured."""
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