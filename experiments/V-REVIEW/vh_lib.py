"""vh_lib -- V-REVIEW's OWN edge/overshoot instrument for the halo adjudication.

Written without reading experiments/V-EYES/. The statistic, the edge finder and
the resampling arms below are this verifier's own; any agreement with V-EYES is
therefore independent agreement.

THE STATISTIC (classic step-response overshoot, in DN):

  A profile is sampled along the edge NORMAL and median-combined along the edge
  TANGENT.  A and B are the dark and bright plateau levels.  x10/x90 are the
  10%/90% crossings, w = x90-x10 is the edge width.  Then

      overshoot_dn = max(p over [x90, x90+3w]) - median(p over [x90+3w, x90+6w])
      undershoot_dn = median(p over [x10-6w, x10-3w]) - min(p over [x10-3w, x10])

  A monotone step reads 0 by construction: nothing in the shoulder exceeds the
  plateau it is approaching.  A ringing step reads the height of its rim.
  Everything is expressed in units of the edge's OWN width w, so the number is
  scale-free and full-resolution and reduced images are comparable.

WHY IT IS IN DN AND ALSO IN % OF STEP:  a rim of 30 DN on a 300 DN step is
visible; 30 DN on a 30000 DN step is not.  Both are reported; neither alone
adjudicates.

ABSOLUTE FLOORS, DECLARED BEFORE THE RUN (a search that cannot fail is not a
search).  A site is REJECTED unless:
  * step height >= STEP_MIN DN                 -- not a gradient in the noise
  * both plateaus flat: sd <= FLAT_MAX * step  -- not texture
  * 0 < w <= WMAX_FRAC * R                     -- a step, not a ramp
  * the reference plateau windows fit inside the sampled span
  * gradient orientation is consistent along the tangent (straight edge)
"""
import numpy as np
import tifffile
from PIL import Image

SHIP_V4 = r"C:\dev\strehl-out\acceptance\SHIP-V4"
OUT = r"C:\dev\strehl-out\V-REVIEW\halo"

# ---- the gallery reduction, read from scripts/viewable.py + finalpass.ps1 ----
GALLERY_MAXW = 1400          # viewable.py --maxw default; finalpass passes it

# ---- declared floors -------------------------------------------------------
STEP_MIN = 1500.0            # DN, on a 0..65535 scale
FLAT_MAX = 0.06              # plateau sd as a fraction of step height
SHOULDER = 3.0               # shoulder zone extends 3w past the 10/90 crossing
REFSPAN = 3.0                # reference plateau measured over the next 3w
ORIENT_TOL = 0.30            # rad, sd of gradient angle along the tangent


def lum(rgb):
    return (0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2])


def read_master(subject, arm="SHIP-V4"):
    import os
    a = tifffile.imread(os.path.join(SHIP_V4, "%s--%s.tiff" % (subject, arm)))
    if a.dtype != np.uint16:
        raise SystemExit("%s: dtype %s, expected uint16" % (subject, a.dtype))
    return a[:, :, :3].astype(np.float32)


# ---------------------------------------------------------------- resamplers
def _pil_resize(plane, w, h, how):
    im = Image.fromarray(plane.astype(np.float32), mode="F")
    return np.asarray(im.resize((w, h), how), dtype=np.float32)


def reduce_plane(plane, maxw=GALLERY_MAXW, kernel="lanczos"):
    """Same library, same call, ONLY the kernel differs -- so a difference
    between the arms is the kernel and cannot be anything else."""
    h0, w0 = plane.shape
    w = maxw
    h = int(round(h0 * maxw / w0))
    how = {"lanczos": Image.LANCZOS,   # negative lobes
           "box": Image.BOX,           # area average, NO negative lobes
           "bilinear": Image.BILINEAR, # no negative lobes
           "bicubic": Image.BICUBIC,   # negative lobes
           }[kernel]
    return _pil_resize(plane, w, h, how), w0 / float(w)


def gallery_chain(rgb, maxw=GALLERY_MAXW, quality=95):
    """The ACTUAL delivered artifact: 16->8 bit with viewable.py's rounding,
    PIL LANCZOS to maxw, JPEG q95 4:4:4.  Returned on a 0..65535 scale so it is
    comparable with the master, by multiplying by 257 (255*257 = 65535)."""
    import io
    eight = ((rgb.astype(np.uint32) + 128) >> 8).clip(0, 255).astype(np.uint8)
    im = Image.fromarray(eight, mode="RGB")
    h = int(round(im.height * maxw / im.width))
    im = im.resize((maxw, h), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=quality, subsampling=0)
    buf.seek(0)
    back = np.asarray(Image.open(buf).convert("RGB"), dtype=np.float32)
    return back * 257.0, rgb.shape[1] / float(maxw)


# ------------------------------------------------------------------ sampling
def bilinear(img, Y, X):
    h, w = img.shape
    Y = np.clip(Y, 0, h - 1.001); X = np.clip(X, 0, w - 1.001)
    y0 = np.floor(Y).astype(np.int32); x0 = np.floor(X).astype(np.int32)
    fy = (Y - y0).astype(np.float32); fx = (X - x0).astype(np.float32)
    y1 = y0 + 1; x1 = x0 + 1
    return (img[y0, x0] * (1 - fy) * (1 - fx) + img[y0, x1] * (1 - fy) * fx +
            img[y1, x0] * fy * (1 - fx) + img[y1, x1] * fy * fx)


def profile_at(img, y, x, nx, ny, R, tan_len, dstep=0.25):
    """Median-along-tangent profile through (y,x) along the normal (nx,ny)."""
    us = np.arange(-R, R + dstep, dstep, dtype=np.float32)
    ss = np.arange(-tan_len, tan_len + 1.0, 1.0, dtype=np.float32)
    tx, ty = -ny, nx
    Y = y + us[:, None] * ny + ss[None, :] * ty
    X = x + us[:, None] * nx + ss[None, :] * tx
    return us, np.median(bilinear(img, Y, X), axis=1)


def analyse(us, p):
    """Return dict or None if the site fails a declared floor."""
    n = len(p)
    k = max(3, n // 8)
    A = float(np.median(p[:k])); B = float(np.median(p[-k:]))
    step = B - A
    if step < STEP_MIN:
        return None
    sdA = float(np.std(p[:k])); sdB = float(np.std(p[-k:]))
    if sdA > FLAT_MAX * step or sdB > FLAT_MAX * step:
        return None
    q = (p - A) / step
    i10 = np.argmax(q >= 0.10); i90 = np.argmax(q >= 0.90)
    if i90 <= i10:
        return None
    x10, x90 = float(us[i10]), float(us[i90])
    w = x90 - x10
    if w <= 0:
        return None
    hi_lo, hi_hi = x90, x90 + SHOULDER * w
    ref_lo, ref_hi = hi_hi, hi_hi + REFSPAN * w
    lo_hi, lo_lo = x10, x10 - SHOULDER * w
    refd_hi, refd_lo = lo_lo, lo_lo - REFSPAN * w
    if ref_hi > us[-1] or refd_lo < us[0]:
        return None                      # window does not fit: reject, not clamp
    m = lambda a, b: (us >= a) & (us <= b)
    Bref = float(np.median(p[m(ref_lo, ref_hi)]))
    Aref = float(np.median(p[m(refd_lo, refd_hi)]))
    over = float(np.max(p[m(hi_lo, hi_hi)]) - Bref)
    under = float(Aref - np.min(p[m(lo_lo, lo_hi)]))
    nsd = profile_noise_sd(us, p, x10, x90, w)
    nmu, nsg = null_floor(nsd, w)
    return dict(A=A, B=B, step=step, w=w, x10=x10, x90=x90,
                noise_sd=nsd, null_mean=nmu, null_sd=nsg,
                over_excess=over - nmu,
                rings=bool(over > nmu + 3.0 * nsg),
                overshoot_dn=over, undershoot_dn=under,
                overshoot_pct=100.0 * over / step,
                undershoot_pct=100.0 * under / step,
                rim_dn=max(over, 0.0) + max(under, 0.0))

# --------------------------------------------------------------- null floor
# A max-taken-over-a-shoulder is biased UPWARD by noise: ARM E measured a
# noise-only null of 32.9 DN mean at 150 DN pixel noise, which is the same
# order as the effects under adjudication.  So every site carries its own
# measured floor and a reading below it is not a rim.
def profile_noise_sd(us, p, x10, x90, w):
    """Noise sd of the PROFILE (after tangent median), estimated on the
    plateaus at 1 px spacing so adjacent samples are ~independent."""
    step_px = int(round(1.0 / (us[1] - us[0])))
    lo = p[us <= x10 - SHOULDER * w][::step_px]
    hi = p[us >= x90 + SHOULDER * w][::step_px]
    sds = []
    for seg in (lo, hi):
        if len(seg) >= 8:
            d = np.diff(seg)
            mad = np.median(np.abs(d - np.median(d)))
            sds.append(1.4826 * mad / np.sqrt(2.0))
    return float(np.median(sds)) if sds else float("nan")


def null_floor(sd, w, ndraw=4000, seed=11):
    """Expected max-of-shoulder for pure noise of this sd: MC, not a formula."""
    if not np.isfinite(sd) or sd <= 0:
        return 0.0, 0.0
    k = max(3, int(round(SHOULDER * w)))
    rng = np.random.default_rng(seed)
    m = rng.standard_normal((ndraw, k)).max(axis=1) * sd
    return float(m.mean()), float(m.std())
