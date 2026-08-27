"""COMMISSIONING: does each ringing statistic respond to what it claims?

Every arm is a synthetic image with GROUND TRUTH, pushed through the identical
machinery.  Required of an honest ringing metric:

  NULL      identical bytes -> identical number (resolution floor)
  CLEAN     a monotone-blurred step has NO ringing -> must read ~0
  RING      a planted overshoot lobe -> must read RED, monotone in amplitude
  IMPROVE   a planted, unambiguous IMPROVEMENT -> must NOT read worse
"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from instr import A_stat, B_stat, C_stat, step_overshoot, edge_energy

H = W = 700
STEP = 1000.0
rng = np.random.default_rng(7)


def gauss1d(sig, rad=None):
    rad = rad or max(1, int(np.ceil(4 * sig)))
    t = np.arange(-rad, rad + 1)
    k = np.exp(-t * t / (2 * sig * sig))
    return k / k.sum()


def sepconv(img, k):
    p = len(k) // 2
    a = np.apply_along_axis(lambda m: np.convolve(m, k, "same"),
                            1, np.pad(img, ((0, 0), (p, p)), mode="edge"))[:, p:-p]
    a = np.apply_along_axis(lambda m: np.convolve(m, k, "same"),
                            0, np.pad(a, ((p, p), (0, 0)), mode="edge"))[p:-p, :]
    return a


def base_step(sig, noise=0.0, tilt=True):
    """A step edge, slightly tilted so the profile machinery sees many phases."""
    x = np.arange(W)[None, :].astype(np.float64)
    y = np.arange(H)[:, None].astype(np.float64)
    u = x - (W / 2 + (0.06 * (y - H / 2) if tilt else 0.0))
    img = STEP * (u > 0).astype(np.float64)
    img = sepconv(img, gauss1d(sig))
    if noise:
        img = img + rng.normal(0, noise, img.shape)
    return img


def add_ring(img, dist, width, amp):
    """Add an antisymmetric overshoot lobe at +-`dist` px from the edge."""
    x = np.arange(W)[None, :].astype(np.float64)
    y = np.arange(H)[:, None].astype(np.float64)
    u = x - (W / 2 + 0.06 * (y - H / 2))
    ring = amp * STEP * np.exp(-((np.abs(u) - dist) ** 2) / (2.0 * width ** 2))
    ring = np.where(u < 0, -ring, ring)
    return img + ring


def unsharp(img, sig, k):
    return img + k * (img - sepconv(img, gauss1d(sig)))


def alias_arm(img, phase=0):
    """The HALF-RES PLANE GATHER, faithfully: decimate 2x (take one phase, no
    prefilter -> aliasing), warp/gather on that lattice, then place back on the
    full grid by linear interpolation. This is what warp_frame_in_place_plane
    does to content above the plane Nyquist."""
    small = img[phase::2, phase::2]
    # gather with a half-pixel shift on the SMALL lattice (a warp), catmull-rom
    k = np.array([-0.0625, 0.5625, 0.5625, -0.0625])   # Catmull-Rom at t=0.5
    sm = np.apply_along_axis(lambda m: np.convolve(m, k, "same"), 1, small)
    out = np.repeat(np.repeat(sm, 2, axis=0), 2, axis=1)[:img.shape[0], :img.shape[1]]
    return out


def fullres_arm(img):
    """The FULL-RES GATHER: same half-pixel Catmull-Rom shift, but on the full
    lattice, then sampled at the same output sites."""
    k = np.array([-0.0625, 0.5625, 0.5625, -0.0625])
    return np.apply_along_axis(lambda m: np.convolve(m, k, "same"), 1, img)


def zone_plate():
    """A radial chirp: unambiguous ground truth for aliasing. Frequency rises
    with radius, so the half-res arm MUST fold the outer rings back in."""
    y, x = np.mgrid[0:H, 0:W].astype(np.float64)
    r = np.hypot(y - H / 2, x - W / 2)
    return STEP * 0.5 * (1 + np.cos(0.00125 * r * r))


def row(tag, img, ref=None):
    a = A_stat(img); c = C_stat(img); b = B_stat(img)
    extra = ""
    if ref is not None:
        extra = "  rmse_vs_truth=%9.2f" % float(np.sqrt(((img - ref) ** 2).mean()))
    print("%-34s A=%8.4f (n=%4d) C=%8.4f (n=%4d) B=%7.4f%%  edge=%7.2f%s"
          % (tag, a["over"], a["n"], c["over"], c["n"], 100 * b, edge_energy(img), extra))
    return a["over"], c["over"], b


print("=" * 118)
print("1. NULL -- identical array twice. Any difference is the instrument's own floor.")
print("=" * 118)
n1 = base_step(1.2, noise=3.0)
n2 = n1.copy()
r1 = row("null: image", n1); r2 = row("null: identical copy", n2)
print("   floor  |dA|=%.3e  |dC|=%.3e  |dB|=%.3e" %
      (abs(r1[0] - r2[0]), abs(r1[1] - r2[1]), abs(r1[2] - r2[2])))

print()
print("=" * 118)
print("2. CLEAN -- monotone Gaussian blur. NO ringing exists. An honest ringing metric reads ~0.")
print("=" * 118)
for s in (0.8, 1.6, 3.0):
    row("clean gaussian sigma=%.1f" % s, base_step(s, noise=3.0))

print()
print("=" * 118)
print("3a. PLANTED WIDE HALO at 30 px (what orch_halo's BAND 16..180 full-res px is aimed at)")
print("=" * 118)
for amp in (0.0, 0.02, 0.05, 0.10, 0.20):
    row("wide halo d=30 w=12 amp=%.2f" % amp, add_ring(base_step(1.2, noise=3.0), 30, 12, amp))

print()
print("=" * 118)
print("3b. PLANTED NARROW RING at 2 px -- THE ringing a Catmull-Rom / Malvar lobe makes")
print("=" * 118)
for amp in (0.0, 0.02, 0.05, 0.10, 0.20, 0.40):
    row("narrow ring d=2 w=1.2 amp=%.2f" % amp, add_ring(base_step(1.2, noise=3.0), 2.0, 1.2, amp))

print()
print("=" * 118)
print("3c. UNSHARP MASK -- manufactured halo, the classic sharpening artefact")
print("=" * 118)
b0 = base_step(2.2, noise=3.0)
for k in (0.0, 0.5, 1.0, 2.0):
    row("unsharp sigma=3 k=%.1f" % k, unsharp(b0, 3.0, k))

print()
print("=" * 118)
print("4. PLANTED IMPROVEMENT -- does any statistic score a KNOWN GAIN as worse?")
print("=" * 118)
print("4a. deblur: sigma 3.0 -> 0.8, both monotone, no ringing added anywhere")
row("  worse  (sigma=3.0)", base_step(3.0, noise=3.0))
row("  better (sigma=0.8)", base_step(0.8, noise=3.0))
print()
print("4b. de-alias on a ZONE PLATE: half-res plane gather vs full-res gather,")
print("    scored against the exact same gather applied to the TRUE full-res field.")
zp = zone_plate()
truth = fullres_arm(zp)
row("  half-res plane gather (aliased)", alias_arm(zp), ref=truth)
row("  full-res gather (correct)      ", fullres_arm(zp), ref=truth)
print()
print("4c. de-alias on a TILTED STEP with fine texture riding on it")
tex = base_step(1.0, noise=0.0)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
tex = tex + 60.0 * np.cos(2 * np.pi * 0.38 * xx) * np.cos(2 * np.pi * 0.11 * yy)
tex = tex + rng.normal(0, 3.0, tex.shape)
truth2 = fullres_arm(tex)
row("  half-res plane gather (aliased)", alias_arm(tex), ref=truth2)
row("  full-res gather (correct)      ", fullres_arm(tex), ref=truth2)

print()
print("=" * 118)
print("5. B's INVARIANCE, stated as a claim and tested: B(a*y+c) == B(y) exactly.")
print("=" * 118)
t = base_step(1.2, noise=3.0)
for a, c in ((1.0, 0.0), (2.0, 0.0), (0.25, 0.0), (1.0, 5000.0), (7.3, -120.0)):
    print("   B(%.2f*y %+8.1f) = %.6f%%" % (a, c, 100 * B_stat(a * t + c)))
