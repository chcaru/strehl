"""widehalo2: edge-local halo profile, immune to frame-scale illumination.

widehalo.py FAILED its LIGHTING specificity arm: a pure full-frame ramp with no
edge coupling scored +10.616 near / +1.062 far, a perfect halo decay and 23x
LARGER than a genuine planted halo. Cause: edges are not uniformly distributed,
so distance-from-edge is correlated with position-in-frame and ANY global
gradient projects onto the distance axis. That is V-REVIEW's false-positive mode
reproduced exactly. The arm row had the same monotone shape, so it was void.

FIX. Subtract a local mean over a window far larger than any halo (W=1025 px)
before profiling. A frame-scale ramp is flat within that window and cancels; a
2-512 px halo survives.

ACCEPTANCE, stated before looking: the planted WIDE-HALO must exceed BOTH
specificity arms by >=5x in the mid bins. Sensitivity alone is not commissioning.
"""
import sys, numpy as np, tifffile
from scipy import ndimage
EDGES = [2, 4, 8, 16, 32, 64, 128, 256, 512]
W = 1025

def luma(p):
    a = np.asarray(tifffile.imread(p), np.float64)
    if a.ndim == 3: a = 0.2126*a[...,0] + 0.7152*a[...,1] + 0.0722*a[...,2]
    return a

def detrend(g):
    return g - ndimage.uniform_filter(g, size=W, mode="nearest")

def profile(g, dist):
    d = detrend(g)
    return np.array([d[(dist >= EDGES[i]) & (dist < EDGES[i+1])].mean()
                     for i in range(len(EDGES)-1)])

A, B, TAG = sys.argv[1], sys.argv[2], sys.argv[3]
gA, gB = luma(A), luma(B)
s = ndimage.gaussian_filter(gA, 2.0); gm = np.hypot(*np.gradient(s))
em = gm > np.percentile(gm, 99.0)
dist = ndimage.distance_transform_edt(~em)
pA = profile(gA, dist)
print("%s  edges %.2f%%  max dist %.0f px  detrend W=%d" % (TAG, 100*em.mean(), dist.max(), W))
hdr = "  ".join("%7s" % ("%d-%d" % (EDGES[i], EDGES[i+1])) for i in range(len(EDGES)-1))
print("\n  %-44s %s" % ("delta vs A, DN, local-detrended", hdr))

def show(name, gX):
    d = profile(gX, dist) - pA
    print("  %-44s %s" % (name, "  ".join("%7.3f" % v for v in d)))
    return d

glow = ndimage.gaussian_filter(em.astype(np.float64), 60.0); glow /= glow.max()
narrow = ndimage.gaussian_filter(em.astype(np.float64), 3.0); narrow /= narrow.max()
amp = 0.02 * np.median(gA)
rng = np.random.default_rng(7)
yy = np.linspace(-1, 1, gA.shape[0])[:, None] * np.ones((1, gA.shape[1]))
print("  --- COMMISSIONING ---")
w  = show("WIDE-HALO   sigma=60  -> must RISE",          gA + amp*glow)
n  = show("NARROW-HALO sigma=3   -> must RISE near",     gA + amp*narrow)
r  = show("HALO-REMOVAL          -> must FALL",          gA - amp*glow)
nz = show("NOISE indep.          -> must NOT move",      gA + rng.normal(0, amp*3, gA.shape))
lt = show("LIGHTING ramp         -> must NOT move",      gA + amp*4*yy)
mid = slice(2, 7)
sw = np.max(np.abs(w[mid])); sn = np.max(np.abs(nz)); sl = np.max(np.abs(lt))
print("  --- commissioning result ---")
print("     wide-halo mid |d| = %.4f   noise max |d| = %.4f   lighting max |d| = %.4f" % (sw, sn, sl))
ok = [("WIDE rises",        np.max(w[mid]) > 0),
      ("REMOVAL falls",     np.min(r[mid]) < 0),
      ("NARROW near-biased", abs(n[0]) > abs(n[4])),
      ("SPEC vs noise >=5x", sw >= 5*sn),
      ("SPEC vs lighting >=5x", sw >= 5*sl)]
for k, v in ok: print("     %-24s %s" % (k, "PASS" if v else "*** FAIL ***"))
np_ = sum(v for _, v in ok); print("     COMMISSIONED %d/5" % np_)
print("  --- THE ARM UNDER TEST ---")
d = show("B - A  (real arm)", gB)
print("     arm mid |d| = %.4f vs lighting floor %.4f -> %s"
      % (np.max(np.abs(d[mid])), sl,
         "ABOVE confound floor" if np.max(np.abs(d[mid])) >= 5*sl else "BELOW/NEAR confound floor"))
if np_ < 5: print("  NOT COMMISSIONED -- arm row NOT quotable")
