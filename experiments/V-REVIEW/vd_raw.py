"""Raw-domain dust stack -- the strongest test available without new capture.

Dust is fixed in SENSOR coordinates. Raw frames are unaligned and unwarped, so
at a fixed sensor coordinate the dust is stationary while subject detail varies
from subject to subject. Median across many DIFFERENT subjects therefore
suppresses subject and keeps dust -- the raw-domain analogue of vd_stack.py.

Splitting the subjects into CPL and non-CPL answers the question the flats
cannot: a mote on the CPL cannot appear in the non-CPL group.
"""
import numpy as np, cv2, os, glob, rawpy

BLACK = 512.0
MOTE = (3419, 2316)
CTRL = [(3400, 2300), (1717, 1152), (1200, 800), (2600, 1500),
        (900, 1800), (3419, 1500), (2000, 2316)]
SRC = r"D:\personal\macro"


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
    model = (Xa @ coef).reshape(sub.shape)
    cm = rr <= core
    med = np.median(model[cm])
    if med <= 0:
        return None
    return float(1.0 - np.median(sub[cm]) / med)     # median, not min: unbiased


subs = sorted(d for d in os.listdir(SRC)
              if os.path.isdir(os.path.join(SRC, d)) and d != "flat-fields")
cpl = [s for s in subs if s.endswith("-cpl")]
non = [s for s in subs if not s.endswith("-cpl")]
print("subjects: %d cpl, %d non-cpl" % (len(cpl), len(non)))

PLANT = None


def load(subj, plant=None):
    fs = sorted(glob.glob(os.path.join(SRC, subj, "*.ARW")))
    if not fs:
        return None
    with rawpy.imread(fs[len(fs) // 2]) as r:
        a = r.raw_image_visible.astype(np.float32) - BLACK
    b = bin2(a)
    m = np.median(b)
    if m <= 0:
        return None
    b = b / m
    if plant is not None:
        px, py, amp = plant
        yy, xx = np.mgrid[0:b.shape[0], 0:b.shape[1]]
        b = b * (1.0 - amp * np.exp(-(((xx - px) ** 2 + (yy - py) ** 2) / (2.0 * 12.0 ** 2))))
    return cv2.GaussianBlur(b, (0, 0), 2.0)


def run(group, name, plant=None):
    per = {s: [] for s in ["MOTE"] + ["c%d" % i for i in range(len(CTRL))]}
    used = 0
    for subj in group:
        F = load(subj, plant)
        if F is None:
            continue
        d = quad_depth(F, *MOTE)
        if d is None:
            continue
        per["MOTE"].append(d)
        for i, c in enumerate(CTRL):
            v = quad_depth(F, *c)
            if v is not None:
                per["c%d" % i].append(v)
        used += 1
    print("\n  %s  (%d subjects stacked)" % (name, used))
    med = {k: (100 * float(np.median(v)) if v else None) for k, v in per.items()}
    ctrls = [med["c%d" % i] for i in range(len(CTRL)) if med["c%d" % i] is not None]
    print("    MOTE      %+7.3f%%" % med["MOTE"])
    print("    controls  %s" % "  ".join("%+.3f" % c for c in ctrls))
    print("    control mean %+.3f%%   sd %.3f pts" % (np.mean(ctrls), np.std(ctrls)))
    z = (med["MOTE"] - np.mean(ctrls)) / max(np.std(ctrls), 1e-9)
    print("    MOTE vs controls: %+.3f pts  = %+.2f control-sd" %
          (med["MOTE"] - np.mean(ctrls), z))
    return used, med["MOTE"], np.mean(ctrls), np.std(ctrls)


print("\n" + "=" * 70)
print("REAL DATA")
print("=" * 70)
run(cpl, "CPL subjects")
run(non, "NON-CPL subjects")

print("\n" + "=" * 70)
print("COMMISSION: plant a 3% dip at the MOTE site into every raw frame")
print("=" * 70)
run(non, "NON-CPL + planted 3% at MOTE", plant=(MOTE[0], MOTE[1], 0.03))
print("\n  and a 1% plant, to find the floor")
run(non, "NON-CPL + planted 1% at MOTE", plant=(MOTE[0], MOTE[1], 0.01))
