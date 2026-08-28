r"""COMMISSION ORCH's experiments/ORCH-drift-check/contrast_ab.py.

contrast_ab.py is invoked VERBATIM as a subprocess on planted TIFFs, so this
tests the committed instrument and not my reading of it. contrast_ab.py is
ORCH's file and is never opened for writing here.

Its stated decision rule is:
    "a good arm has FLAT well below 1 and EDGE at ~1.0"
ORCH has asked V-BANDFLOOR to score a ladder on FLAT < 1 and EDGE >= 0.98.

THE QUESTION: can that rule tell an HONEST DENOISE (removes only noise) from a
FLAT-REGION BLUR (removes real, reproducible scene texture)? Both drive FLAT
below 1 and leave EDGE at 1.0. If they read alike the rule cannot express the
difference, and a knob that destroys real low-contrast texture scores as a win.

PLANT SIZING (v2): plants are sized in the HIGH-PASS std at the flat tiles --
the same statistic contrast_ab.py reports -- not the raw tile std. v1 sized on
raw tile std (4608 DN) and produced a 12x plant, far outside the regime.
The honest-denoise plant is also confined to the flat tiles, so that removing
it leaves EDGE untouched; v1 added noise globally and so depressed EDGE for a
reason that was the plant's fault, not the instrument's.
"""
import os
import subprocess
import sys

import numpy as np
import tifffile
from scipy.ndimage import gaussian_filter
from scipy.signal import fftconvolve

CAB = r"C:\dev\blog\death-of-software\projects\strehl\experiments\ORCH-drift-check\contrast_ab.py"
WORK = r"C:\dev\strehl-out\V-BANDFLOOR\cab"
os.makedirs(WORK, exist_ok=True)
S = 256


def lum(a):
    if a.ndim == 3:
        return a[..., :3].astype(np.float64) @ np.array([0.2126, 0.7152, 0.0722])
    return a.astype(np.float64)


def sites(a):
    """Replicate contrast_ab.py's OWN site choice exactly."""
    g = np.hypot(*np.gradient(a))
    H, W = a.shape
    ny, nx = H // S, W // S
    tg = g[:ny * S, :nx * S].reshape(ny, S, nx, S).mean(axis=(1, 3))
    order = np.argsort(tg.ravel())
    out = []
    for grp in (order[:12], order[-12:]):
        m = np.zeros(a.shape, bool)
        for f in grp:
            ty, tx = divmod(int(f), nx)
            m[ty * S:(ty + 1) * S, tx * S:(tx + 1) * S] = True
        out.append(m)
    return out


def hp(x):
    return x - fftconvolve(x, np.ones((3, 3)) / 9.0, mode="same")


def save(path, arr, ref):
    tifffile.imwrite(path, np.clip(arr, 0, 65535).astype(ref.dtype))


def cab(pa, pb, tag, expect):
    r = subprocess.run([sys.executable, CAB, pa, pb], capture_output=True, text=True)
    out = r.stdout + r.stderr
    fl = ed = None
    for ln in out.splitlines():
        if ln.startswith("FLAT"):
            fl = float(ln.split("ratio B/A =")[1].split("|")[0])
        if ln.startswith("EDGE"):
            ed = float(ln.split("ratio B/A =")[1].split("|")[0])
    rule = (fl < 1.0 and ed >= 0.98)
    print("  %-16s FLAT %.4f  EDGE %.4f   ORCH rule: %-18s (%s)"
          % (tag, fl, ed, "PASSES -> 'a win'" if rule else "rejected", expect))
    return fl, ed, rule


src = sys.argv[1]
raw = tifffile.imread(src)
a = lum(raw)
fm, em = sites(a)
loc = float(hp(a)[fm].std())
print("COMMISSIONING contrast_ab.py (invoked verbatim) on %s" % os.path.basename(src))
print("  shape %s dtype %s   flat-site high-pass std = %.1f DN (plants sized in these units)\n"
      % (raw.shape, raw.dtype, loc))

rng = np.random.default_rng(3)
m3 = (lambda m: m[..., None] if raw.ndim == 3 else m)
pA = os.path.join(WORK, "A.tiff")
save(pA, raw, raw)
F = raw.astype(np.float64)

cab(pA, pA, "null", "both 1.0")

nz_flat = rng.normal(0, 0.8 * loc, raw.shape) * m3(fm)
pN = os.path.join(WORK, "noisy.tiff")
save(pN, F + nz_flat, raw)
cab(pA, pN, "add-noise", "FLAT must RISE")

# honest denoise: reference is the noisy image, arm is the clean original.
# removes ONLY the planted noise and zero real content -> the TRUE positive.
cab(pN, pA, "honest-denoise", "the TRUE positive")

# flat-region blur: destroys REAL texture exactly where the metric looks,
# removes no noise preferentially -> the FALSE positive under test.
bl = gaussian_filter(F, (1.2, 1.2, 0) if raw.ndim == 3 else 1.2)
pFB = os.path.join(WORK, "flatblur.tiff")
save(pFB, np.where(m3(fm), bl, F), raw)
cab(pA, pFB, "flat-blur", "the FALSE positive")

pGB = os.path.join(WORK, "globalblur.tiff")
save(pGB, bl, raw)
cab(pA, pGB, "global-blur", "EDGE must catch it")
