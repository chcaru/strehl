"""The one arm with the power to decide: two merges over IDENTICAL frames.

Everything the absolute statistic could not separate -- lens vignetting, the
physical shadow, unmasked subject material, illumination falloff -- is common
mode between two merges of the same 205/299/105 frames and cancels in the
difference. The only thing that differs is the merge backend.

pyramid   = the SHIPPING DEFAULT. Proven byte-identical to the master.
estimator = the pre-switch default, the arm the README's aura finding was
            actually measured on.

Exposure for each subject is read out of that subject's own master provenance,
so the two arms land in one photometric space rather than two auto-exposures.
"""
import os, re, sys, json, subprocess
import numpy as np, tifffile
from scipy import ndimage
sys.path.insert(0, r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-REVIEW")
import vr_lib as V

ACC = r"C:\dev\strehl-out\acceptance\SHIP-V4"
OUT = r"C:\dev\strehl-out\V-REVIEW\aura-ship"
LEVEL = 257.0
BANDS = [(20, 50), (50, 80), (80, 200), (200, 400)]
SUBJECTS = ["flower-bud-alone-cpl", "coffee-bean", "wrapped-text-1",
            "bee-1-cpl", "lavendar-cpl"]
seal, _ = V.corpus_seal(ACC, "SHIP-V4")
EXE, PIN = V.pin_for(seal)
env = {k: v for k, v in os.environ.items() if not k.startswith("STREHL_")}


def expo(sub):
    t = open(os.path.join(ACC, "%s--SHIP-V4.tiff.provenance.txt" % sub)).read()
    m = re.search(r"--exposure[= ]\+?(-?[\d.]+)", t)
    return m.group(1)


def render(sub, tag, extra):
    p = os.path.join(OUT, "%s--%s.tiff" % (sub, tag))
    if os.path.exists(p):
        return p
    cmd = [EXE, "stack", os.path.join(r"D:\personal\macro", sub), "--out", p,
           "--srgb", "--exposure=%s" % expo(sub)] + extra
    print("    rendering %s %s (exposure %s)" % (sub, tag, expo(sub)), flush=True)
    r = subprocess.run(cmd, env=env, capture_output=True, timeout=7200)
    if r.returncode != 0:
        print(r.stderr.decode("utf-8", "replace")[-1200:]); raise SystemExit(1)
    open(p + ".ok", "w").write(V._sha256(EXE))
    open(p + ".provenance.txt", "w").write(
        "binary %s\npin %s\nsha256 %s\ncorpus-seal %s\nargv %s\nSTREHL_* cleared\n"
        % (EXE, PIN, V._sha256(EXE), seal, " ".join(cmd)))
    return p


def luma(a): return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
def rd(p): return luma(tifffile.imread(p).astype(np.float64))[::4, ::4]


def otsu(v):
    h, _ = np.histogram(v, bins=512, range=(0, 65535)); h = h.astype(np.float64)
    w = np.cumsum(h); m = np.cumsum(h * np.arange(512)); tot, mt = w[-1], m[-1]
    with np.errstate(invalid="ignore", divide="ignore"):
        vb = (mt * w / tot - m) ** 2 / (w * (tot - w))
    vb[~np.isfinite(vb)] = -1
    return (np.argmax(vb) + 0.5) * 65535.0 / 512.0


def geom(a):
    t = otsu(a); d = a < t
    if d.mean() > 0.5: d = ~d
    d = ndimage.binary_closing(ndimage.binary_opening(d, np.ones((5, 5))), np.ones((9, 9)))
    lab, k = ndimage.label(d)
    if k == 0: return None
    sz = ndimage.sum(d, lab, range(1, k + 1))
    d = ndimage.binary_fill_holes(lab == (int(np.argmax(sz)) + 1))
    if d.mean() < 0.002 or d.mean() > 0.75: return None
    return d, ndimage.distance_transform_edt(~d) * 4.0


def prof(a, d, dt):
    far = (dt >= 800) & (dt < 2000) & (~d)
    if far.sum() < 5000: far = (dt >= 400) & (~d)
    f = np.median(a[far]); o = {}
    for lo, hi in BANDS:
        m = (dt >= lo) & (dt < hi) & (~d)
        o[(lo, hi)] = float(f - np.median(a[m])) if m.sum() >= 400 else None
    return f, o


print("=" * 78)
print("CONTROL A  second byte-exact reproduction of a shipping master")
print("=" * 78)
import hashlib
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest().upper()
cb = render("coffee-bean", "pyramid", ["--merge", "pyramid"])
hm = sha(os.path.join(ACC, "coffee-bean--SHIP-V4.tiff")); hp = sha(cb)
print("  coffee-bean master %s" % hm)
print("  coffee-bean arm P  %s" % hp)
print("  IDENTICAL: %s  -> masters may be used as the pyramid arm" % (hm == hp))

print()
print("=" * 78)
print("CONTROL B  an arm that CANNOT show a merge difference")
print("=" * 78)
a = rd(cb); g = geom(a); f0, p0 = prof(a, g[0], g[1])
f1, p1 = prof(a.copy(), g[0], g[1])
print("  same pixels differenced against themselves: %+.6f DN at 80-200"
      % (p1[(80, 200)] - p0[(80, 200)]))

print()
print("=" * 78)
print("CONTROL C  planted smooth aura must be recovered by the DIFFERENCE")
print("=" * 78)
for amp in (1.0, 4.0):
    fall = np.clip(1.0 - g[1] / 300.0, 0, 1) * (~g[0])
    _, pq = prof(a - fall * amp * LEVEL, g[0], g[1])
    got = (pq[(80, 200)] - p0[(80, 200)]) / LEVEL
    exp = amp * (1 - 140.0 / 300.0)
    print("  planted %.1f levels -> recovered %+.2f levels (expect ~%+.2f)  %s"
          % (amp, got, exp, "PASS" if abs(got - exp) < 0.35 * exp else "FAIL"))

print()
print("=" * 78)
print("MEASUREMENT  aura of the SHIPPING default relative to the old default")
print("negative = the shipping pyramid merge is BRIGHTER near the subject,")
print("i.e. it veils LESS than the arm the README finding was measured on")
print("=" * 78)
print("  %-30s %9s %9s %9s %9s %9s" % ("subject", "dlevel", "20-50", "50-80", "80-200", "200-400"))
rows = {}
for sub in SUBJECTS:
    mp = os.path.join(ACC, "%s--SHIP-V4.tiff" % sub)
    ep = render(sub, "estimator", ["--merge", "estimator"])
    A, B = rd(mp), rd(ep)
    g = geom(A)
    if g is None:
        print("  %-30s REFUSED (no subject/ground split)" % sub); continue
    d, dt = g
    fa, pa = prof(A, d, dt); fb, pb = prof(B, d, dt)
    r = {}
    for b in BANDS:
        r["%d-%d" % b] = None if (pa[b] is None or pb[b] is None) else (pa[b] - pb[b]) / LEVEL
    rows[sub] = r
    print("  %-30s %9.2f %9s %9s %9s %9s" % (sub, (fa - fb) / LEVEL,
          *[("%+.2f" % r["%d-%d" % b]) if r["%d-%d" % b] is not None else "refuse" for b in BANDS]))
json.dump(rows, open(os.path.join(OUT, "pyr_vs_est.json"), "w"), indent=1)
print()
print("  dlevel = whole-image far-field level difference between the arms.")
print("  The band numbers are self-referenced, so dlevel does not enter them.")
