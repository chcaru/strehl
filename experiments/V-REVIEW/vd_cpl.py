"""Settle two things the dust adjudication rests on.

(1) vd_flat.py's docstring ASSERTS the two exposure ramps are "one with CPL one
    without". The split is int(name[3:8])<300 -- a filename number. That is a
    declaration, never a measurement, and if it is wrong then "reproduces across
    two independent ramps" does not rule out contamination on the FILTER.

(2) The corpus has directories that ARE definitively labelled:
    subject-focus-sweep-with-cpl and subject-focus-sweep-no-cpl. A mote on the
    CPL appears only in the with-cpl arm. A mote on the sensor appears in both.
    The ratio of the two arms cancels the subject and isolates the filter.

Also repairs the vd_quad wrong-sign arm, which was previously planted at a site
that already carried a real dip and so could not fail.
"""
import numpy as np, cv2, os, glob, json, rawpy, exifread

D = r"C:\dev\strehl-out\V-REVIEW\dust"
FLATS = r"D:\personal\macro\flat-fields\flat-fields"
SWEEP = r"D:\personal\macro\flat-fields"
BLACK = 512.0
MOTE = (3419, 2316)                       # binned, deepest point of the plateau
CTRL = [(3400, 2300), (1717, 1152), (1200, 800), (2600, 1500), (900, 1800)]


def bin2(a):
    h, w = a.shape[0] // 2 * 2, a.shape[1] // 2 * 2
    return a[:h:2, :w:2] + a[1:h:2, :w:2] + a[:h:2, 1:w:2] + a[1:h:2, 1:w:2]


def quad_depth(F, x, y, win=45, core=8):
    h, w = F.shape
    y0, y1 = max(0, y - win), min(h, y + win + 1)
    x0, x1 = max(0, x - win), min(w, x + win + 1)
    sub = F[y0:y1, x0:x1].astype(np.float64)
    gy, gx = np.mgrid[y0:y1, x0:x1]
    gy = (gy - y).astype(np.float64); gx = (gx - x).astype(np.float64)
    rr = np.sqrt(gy ** 2 + gx ** 2)
    fit = rr > core + 6
    if fit.sum() < 400:
        return None
    Xc = np.stack([np.ones(fit.sum()), gx[fit], gy[fit],
                   gx[fit] ** 2, gy[fit] ** 2, gx[fit] * gy[fit]], 1)
    coef, *_ = np.linalg.lstsq(Xc, sub[fit], rcond=None)
    Xa = np.stack([np.ones(sub.size), gx.ravel(), gy.ravel(),
                   gx.ravel() ** 2, gy.ravel() ** 2, (gx * gy).ravel()], 1)
    model = (Xa @ Xc[:0].T.sum(1) if False else Xa @ coef).reshape(sub.shape)
    core_m = rr <= core
    return float(1.0 - sub[core_m].min() / np.median(model[core_m]))


print("=" * 72)
print("ARM 1  --  is the 'one with CPL one without' split TRUE?")
print("=" * 72)
names = json.load(open(r"C:\dev\strehl-out\V-REVIEW\good_flats.json"))
rows = {"rampA": [], "rampB": []}
for n in names:
    g = "rampA" if int(n[3:8]) < 300 else "rampB"
    p = os.path.join(FLATS, n)
    with open(p, "rb") as f:
        t = exifread.process_file(f, details=False)
    et = str(t.get("EXIF ExposureTime", "?"))
    fn = str(t.get("EXIF FNumber", "?"))
    iso = str(t.get("EXIF ISOSpeedRatings", "?"))
    dt = str(t.get("EXIF DateTimeOriginal", "?"))
    rows[g].append((n, et, fn, iso, dt))
for g, rs in rows.items():
    ets = [r[1] for r in rs]
    print("  %s  n=%-3d  apertures=%s  ISO=%s" %
          (g, len(rs), sorted(set(r[2] for r in rs)), sorted(set(r[3] for r in rs))))
    print("      shutters: %s" % sorted(set(ets), key=lambda s: eval(s.replace("/", "/1.0/")) if "/" in s else float(s))[:8])
    print("      time span: %s .. %s" % (min(r[4] for r in rs), max(r[4] for r in rs)))

print()
print("  If both ramps share aperture AND ISO AND overlapping shutters and run")
print("  back-to-back in time, they are one optical configuration split by")
print("  filename -- NOT a CPL pair.")

print()
print("=" * 72)
print("ARM 2  --  the LABELLED cpl pair (subject focus sweeps)")
print("=" * 72)


def stack_dir(d, skip=2, limit=30):
    fs = sorted(glob.glob(os.path.join(d, "*.ARW")))[skip:skip + limit]
    acc = None; k = 0
    for p in fs:
        with rawpy.imread(p) as r:
            a = r.raw_image_visible.astype(np.float32) - BLACK
        b = bin2(a)
        m = np.median(b)
        if m <= 0:
            continue
        b /= m
        acc = b if acc is None else acc + b
        k += 1
    return acc / k, k


W, kw = stack_dir(os.path.join(SWEEP, "subject-focus-sweep-with-cpl"))
N, kn = stack_dir(os.path.join(SWEEP, "subject-focus-sweep-no-cpl"))
print("  with-cpl frames %d   no-cpl frames %d   shape %s" % (kw, kn, W.shape))
SW = cv2.GaussianBlur(W, (0, 0), 2.0)
SN = cv2.GaussianBlur(N, (0, 0), 2.0)

print()
print("  site                 with-cpl   no-cpl    difference")
for nm, (x, y) in [("MOTE(3419,2316)", MOTE)] + [("ctrl(%d,%d)" % c, c) for c in CTRL]:
    dw, dn = quad_depth(SW, x, y), quad_depth(SN, x, y)
    if dw is None or dn is None:
        print("  %-20s refused" % nm); continue
    print("  %-20s %+7.2f%%  %+7.2f%%   %+7.2f pts" %
          (nm, 100 * dw, 100 * dn, 100 * (dw - dn)))

print()
print("  RATIO arm: with-cpl / no-cpl cancels the subject; what remains is the")
print("  filter. A dip here means the mote is ON THE CPL.")
R = SW / np.maximum(SN, 1e-6)
R = cv2.GaussianBlur(R, (0, 0), 2.0)
for nm, (x, y) in [("MOTE(3419,2316)", MOTE)] + [("ctrl(%d,%d)" % c, c) for c in CTRL]:
    d = quad_depth(R, x, y)
    print("  %-20s ratio-dip %+7.2f%%" % (nm, 100 * d) if d is not None else "  %-20s refused" % nm)

print()
print("  COMMISSION the ratio arm: plant a 3%% dip into with-cpl ONLY.")
Wp = SW.copy()
yy, xx = np.mgrid[0:Wp.shape[0], 0:Wp.shape[1]]
for (px, py) in [(1200, 800)]:
    g = np.exp(-(((xx - px) ** 2 + (yy - py) ** 2) / (2.0 * 12.0 ** 2)))
    Wp = Wp * (1.0 - 0.03 * g)
Rp = cv2.GaussianBlur(Wp / np.maximum(SN, 1e-6), (0, 0), 2.0)
print("    planted site (1200,800): before %+.2f%%  after %+.2f%%" %
      (100 * quad_depth(R, 1200, 800), 100 * quad_depth(Rp, 1200, 800)))
print("    unplanted MOTE site    : before %+.2f%%  after %+.2f%%" %
      (100 * quad_depth(R, *MOTE), 100 * quad_depth(Rp, *MOTE)))

print()
print("=" * 72)
print("ARM 3  --  REPAIRED wrong-sign arm (planted at a CLEAN site this time)")
print("=" * 72)
A = np.load(os.path.join(D, "flat_rampA.npy")).astype(np.float32)
SA = cv2.GaussianBlur(A, (0, 0), 2.0)
yy, xx = np.mgrid[0:SA.shape[0], 0:SA.shape[1]]
for nm, (px, py) in [("clean mid (1200,800)", (1200, 800)),
                     ("clean corner (3400,2300)", (3400, 2300)),
                     ("OLD arm: on the mote (3434,2305)", (3434, 2305))]:
    base = quad_depth(SA, px, py)
    g = np.exp(-(((xx - px) ** 2 + (yy - py) ** 2) / (2.0 * 10.0 ** 2)))
    bright = SA * (1.0 + 0.05 * g)
    got = quad_depth(bright, px, py)
    ok = "PASS (not a depression)" if got < 0 else "reads as a DEPRESSION"
    print("  %-34s unplanted %+6.2f%%  +5%% bright -> %+6.2f%%   %s"
          % (nm, 100 * base, 100 * got, ok))
