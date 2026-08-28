"""Wide-window halo profile: does the coarse-band arm move anything at 120-400 px?

WHY THIS EXISTS. My reported refutation of ORCH's halo claim used rimv6 /
overshoot.py, whose own docstring says it "can only speak to edges that PLATEAU
within +/-7 px". V-REVIEW has just shown halo_profile.py is void for walking
only 2-120 px with a 400-900 px reference. My window is NARROWER still. The arm
1,8,8,8,8,8,8 raises floors in pyramid levels 1-6; level 6 spans ~64 plane px =
~128 full-sensor px. So the arm acts at scales my instrument cannot see, and my
refutation may be a FALSE NEGATIVE measured at the wrong scale.

STATISTIC. Distance transform from a strong-edge mask, pixels binned by distance
in octaves 2-4-8-...-512 px, mean luma per bin normalised by the FAR bin. A halo
is a near-bin elevation that decays with distance. Reported as B - A per bin, so
any scene content common to both arms cancels.

COMMISSIONING -- five arms, and the last two are the ones that matter:
  WIDE-HALO   planted sigma=60 edge-coupled glow      -> must RISE in mid bins
  NARROW-HALO planted sigma=3                          -> must RISE in near bins only
  HALO-REMOVAL planted negative glow                   -> must FALL   (improvement direction)
  NOISE        independent noise, no edge coupling     -> must NOT move  (SPECIFICITY)
  LIGHTING     smooth full-frame ramp, edge-independent-> must NOT move  (V-REVIEW's
                                                          exact false-positive mode)
Sensitivity without specificity is not commissioning: a metric that only rises
will call a lighting falloff a halo, which is precisely the defect just found.
"""
import sys, numpy as np, tifffile
from scipy import ndimage

EDGES = [2, 4, 8, 16, 32, 64, 128, 256, 512]

def luma(p):
    a = np.asarray(tifffile.imread(p), np.float64)
    if a.ndim == 3: a = 0.2126*a[...,0] + 0.7152*a[...,1] + 0.0722*a[...,2]
    return a

def profile(g, dist):
    """mean luma per distance octave, normalised by the FAR bin"""
    out = []
    for i in range(len(EDGES)-1):
        m = (dist >= EDGES[i]) & (dist < EDGES[i+1])
        out.append(g[m].mean() if m.sum() > 500 else np.nan)
    far = np.nanmean(g[dist >= EDGES[-1]]) if (dist >= EDGES[-1]).sum() > 500 else np.nan
    return np.array(out) / far

def edge_mask(g):
    s = ndimage.gaussian_filter(g, 2.0)
    gm = np.hypot(*np.gradient(s))
    return gm > np.percentile(gm, 99.0)

A, B, TAG = sys.argv[1], sys.argv[2], sys.argv[3]
gA, gB = luma(A), luma(B)
print("%s   A %s   B %s" % (TAG, gA.shape, gB.shape))
em = edge_mask(gA)
dist = ndimage.distance_transform_edt(~em)
print("edge pixels %d (%.2f%%)   max dist %.0f px" % (em.sum(), 100*em.mean(), dist.max()))
pA = profile(gA, dist)

def show(name, gX, expect):
    d = (profile(gX, dist) - pA) * 100.0
    cells = "  ".join("%7.3f" % v for v in d)
    print("  %-46s %s" % (name, cells))
    return d

hdr = "  ".join("%7s" % ("%d-%d" % (EDGES[i], EDGES[i+1])) for i in range(len(EDGES)-1))
print("\n  %-46s %s" % ("delta vs A, x100, normalised by far bin", hdr))

glow = ndimage.gaussian_filter(em.astype(np.float64), 60.0); glow /= glow.max()
narrow = ndimage.gaussian_filter(em.astype(np.float64), 3.0); narrow /= narrow.max()
amp = 0.02 * np.nanmedian(gA)
rng = np.random.default_rng(7)
yy = np.linspace(-1, 1, gA.shape[0])[:, None] * np.ones((1, gA.shape[1]))

print("  --- COMMISSIONING ---")
w  = show("WIDE-HALO   sigma=60  -> must RISE (mid)",      gA + amp*glow,   +1)
n  = show("NARROW-HALO sigma=3   -> must RISE (near)",     gA + amp*narrow, +1)
r  = show("HALO-REMOVAL          -> must FALL",            gA - amp*glow,   -1)
nz = show("NOISE indep.          -> must NOT move (SPEC)", gA + rng.normal(0, amp*3, gA.shape), 0)
lt = show("LIGHTING ramp         -> must NOT move (SPEC)", gA + amp*4*yy,   0)

mid = slice(2, 7)
ok = []
ok.append(("WIDE-HALO rises",   np.nanmax(w[mid]) >  0.05))
ok.append(("NARROW near>mid",   abs(n[0]) > abs(np.nanmax(np.abs(n[mid])))))
ok.append(("REMOVAL falls",     np.nanmin(r[mid]) < -0.05))
ok.append(("NOISE inert",       np.nanmax(np.abs(nz)) < 0.05))
ok.append(("LIGHTING inert",    np.nanmax(np.abs(lt)) < 0.05))
print("  --- commissioning result ---")
for k, v in ok: print("     %-18s %s" % (k, "PASS" if v else "*** FAIL ***"))
npass = sum(v for _, v in ok)
print("     COMMISSIONED %d/5" % npass)

print("  --- THE ARM UNDER TEST ---")
show("B - A  (real arm)", gB, None)
if npass < 5:
    print("  INSTRUMENT NOT FULLY COMMISSIONED -- arm row above is NOT quotable")
