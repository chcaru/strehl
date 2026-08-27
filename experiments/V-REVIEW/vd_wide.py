"""Amplitude, measured with a window sized for the FEATURE.

vd_quad uses win=45 / fit at rr>14. The real mote is ~40-50 binned px across,
so that fit annulus sits partly INSIDE the mote and the quadratic absorbs the
thing being measured. Consequence: the 2.47-3.45% family may be the core
measured against the mote's own shoulders, not against clean field.

Here the fit annulus is pushed outside the feature and the statistic is
commissioned with plants of the SAME WIDTH as the real mote.
"""
import numpy as np, cv2, os

D = r"C:\dev\strehl-out\V-REVIEW\dust"
A = np.load(os.path.join(D, "flat_rampA.npy")).astype(np.float32)
B = np.load(os.path.join(D, "flat_rampB.npy")).astype(np.float32)
SA = cv2.GaussianBlur(A, (0, 0), 2.0)
SB = cv2.GaussianBlur(B, (0, 0), 2.0)
h, w = A.shape
MOTE = (3419, 2316)
CLEAN = [(3400, 2300), (1717, 1152), (1200, 800), (2600, 1500), (900, 1800)]


def depth(F, x, y, win, core, fitmin):
    y0, y1 = max(0, y - win), min(h, y + win + 1)
    x0, x1 = max(0, x - win), min(w, x + win + 1)
    sub = F[y0:y1, x0:x1].astype(np.float64)
    gy, gx = np.mgrid[y0:y1, x0:x1]
    gy = (gy - y).astype(np.float64); gx = (gx - x).astype(np.float64)
    rr = np.sqrt(gy ** 2 + gx ** 2)
    fit = rr > fitmin
    if fit.sum() < 800:
        return None
    Xc = np.stack([np.ones(fit.sum()), gx[fit], gy[fit],
                   gx[fit] ** 2, gy[fit] ** 2, gx[fit] * gy[fit]], 1)
    coef, *_ = np.linalg.lstsq(Xc, sub[fit], rcond=None)
    Xa = np.stack([np.ones(sub.size), gx.ravel(), gy.ravel(),
                   gx.ravel() ** 2, gy.ravel() ** 2, (gx * gy).ravel()], 1)
    model = (Xa @ coef).reshape(sub.shape)
    cm = rr <= core
    med = np.median(model[cm])
    return None if med <= 0 else float(1.0 - np.median(sub[cm]) / med)


yy, xx = np.mgrid[0:h, 0:w]


def plant(F, x, y, amp, sig):
    return F * (1.0 - amp * np.exp(-(((xx - x) ** 2 + (yy - y) ** 2) / (2.0 * sig ** 2))))


CFG = [("narrow  win45  core8  fit>14", 45, 8, 14),
       ("medium  win90  core15 fit>40", 90, 15, 40),
       ("WIDE    win140 core25 fit>70", 140, 25, 70),
       ("WIDER   win200 core25 fit>110", 200, 25, 110)]

print("=" * 78)
print("COMMISSION each configuration with a plant the WIDTH OF THE REAL MOTE")
print("(sigma 20 binned px -> FWHM ~47 px, matching the observed plateau)")
print("=" * 78)
print("%-32s %8s %8s %8s %8s" % ("configuration", "plant2%", "plant5%", "plant8%", "plant13.3%"))
for nm, win, core, fmin in CFG:
    out = []
    for amp in (0.02, 0.05, 0.08, 0.1328):
        vals = []
        for (cx, cy) in CLEAN[:3]:
            base = depth(SA, cx, cy, win, core, fmin)
            got = depth(plant(SA, cx, cy, amp, 20.0), cx, cy, win, core, fmin)
            if base is not None and got is not None:
                vals.append(got - base)
        out.append(100 * float(np.median(vals)) if vals else float("nan"))
    print("%-32s %7.2f%% %7.2f%% %7.2f%% %7.2f%%" % (nm, out[0], out[1], out[2], out[3]))

print()
print("  A configuration is usable only if recovered ~= planted.")
print()
print("=" * 78)
print("THE REAL MOTE, read by each configuration")
print("=" * 78)
print("%-32s %9s %9s %9s" % ("configuration", "rampA", "rampB", "clean-site sd"))
for nm, win, core, fmin in CFG:
    da = depth(SA, MOTE[0], MOTE[1], win, core, fmin)
    db = depth(SB, MOTE[0], MOTE[1], win, core, fmin)
    cs = [depth(SA, cx, cy, win, core, fmin) for (cx, cy) in CLEAN]
    cs = [c for c in cs if c is not None]
    print("%-32s %8.2f%% %8.2f%% %8.2f pts" %
          (nm, 100 * da, 100 * db, 100 * float(np.std(cs))))

print()
print("=" * 78)
print("PROFILE: mote centre vs clean field, straight ratio, no model at all")
print("=" * 78)
cx, cy = MOTE
core = SA[cy - 8:cy + 9, cx - 8:cx + 9]
for rad in (60, 80, 100, 130, 160):
    ann = SA[cy - rad:cy + rad + 1, cx - rad:cx + rad + 1]
    gy, gx = np.mgrid[-rad:rad + 1, -rad:rad + 1]
    rr = np.sqrt(gy ** 2 + gx ** 2)
    ring = ann[(rr > rad - 12) & (rr <= rad)]
    print("  ring r=%3d  core/ring = %.4f  -> depression %5.2f%%   (ring n=%d)"
          % (rad, np.median(core) / np.median(ring),
             100 * (1 - np.median(core) / np.median(ring)), ring.size))
print()
print("  NOTE: a bare ring ratio also contains vignetting between core and ring,")
print("  so it is an UPPER bound on the mote, not a measurement of it.")
