"""COMMISSION halo2. A verdict of "0 HALO" is meaningless until this passes.

Four arms, and the third is the one that matters most:
  A NARROW rim (sigma 14 px)  -> must be CAUGHT. States the floor in DN.
  B BROAD  rim (sigma 40 px)  -> must be CAUGHT. This is the shape the old
                                 instrument could not see at 9000 DN.
  C GRADIENT, no rim          -> must stay CLEAN. This plants the exact
                                 confound that produced all four old false
                                 positives. An instrument that fires here has
                                 not been fixed, it has been renamed.
  D NULL, nothing planted     -> must stay CLEAN.

Arms C and D are the ones that stop me relaxing the instrument into silence
being indistinguishable from correctness: A and B prove it can still fire.
"""
import os, sys
import numpy as np, tifffile
from scipy.ndimage import distance_transform_edt, label

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "ORCH-drift-check"))
import halo_profile as H
import halo2

FAITH = r"C:\dev\strehl-out\ORCH-FAITHFUL\faithful"
HOSTS = ["bee-1-cpl", "flower-bud-alone-cpl"]
AMPS = [100, 200, 400, 800, 1600, 3200]


def field(stem):
    img = tifffile.imread(os.path.join(FAITH, stem + ".tiff"))
    y = H.luma(img).astype(np.float32)
    ys = y[::4, ::4]
    t, subj = H.segment(ys)
    big = np.repeat(np.repeat(subj, 4, 0), 4, 1)[:y.shape[0], :y.shape[1]]
    d = distance_transform_edt(~big).astype(np.float32)
    return y, big, d


def run(y):
    r = halo2.analyse(y)
    return r["verdict"], r.get("amp"), r.get("width"), r.get("why", "")


print("=== BASELINE (nothing planted) ===")
base = {}
for hstem in HOSTS:
    y, big, d = field(hstem)
    v, a, w, why = run(y)
    base[hstem] = (y, big, d, v)
    print("  %-24s %-8s amp %s   %s" % (hstem, v, a, why[:44]))
    assert v == "CLEAN", "host %s is not clean; cannot commission on it" % hstem

print("\n=== ARM A: NARROW rim sigma=14 px at d0=30, host bee-1-cpl ===")
y, big, d, _ = base["bee-1-cpl"]
floorA = None
for A in AMPS:
    rim = A * np.exp(-((d - 30.0) ** 2) / (2 * 14.0 ** 2))
    rim[big] = 0.0
    v, amp, w, why = run(np.clip(y + rim, 0, 65535))
    hit = (v == "HALO")
    if hit and floorA is None: floorA = A
    print("  planted %5d DN -> %-8s measured amp %6s width %5s  %s" % (
        A, v, ("%.0f" % amp) if amp is not None else "-",
        ("%.0f" % w) if w is not None else "-", "CAUGHT" if hit else why[:40]))

print("\n=== ARM B: BROAD rim sigma=40 px at d0=80, host bee-1-cpl ===")
floorB = None
for A in AMPS:
    rim = A * np.exp(-((d - 80.0) ** 2) / (2 * 40.0 ** 2))
    rim[big] = 0.0
    v, amp, w, why = run(np.clip(y + rim, 0, 65535))
    hit = (v == "HALO")
    if hit and floorB is None: floorB = A
    print("  planted %5d DN -> %-8s measured amp %6s width %5s  %s" % (
        A, v, ("%.0f" % amp) if amp is not None else "-",
        ("%.0f" % w) if w is not None else "-", "CAUGHT" if hit else why[:40]))

print("\n=== ARM C: GRADIENT (the confound), host bee-1-cpl -- MUST STAY CLEAN ===")
badC = 0
for A in [1000, 3000, 6000, 9000]:
    g = A * np.exp(-d / 300.0)          # smooth falloff, no rim, width >> 150
    g[big] = 0.0
    v, amp, w, why = run(np.clip(y + g, 0, 65535))
    ok = (v != "HALO")
    if not ok: badC += 1
    print("  gradient %5d DN -> %-8s width %5s  %s" % (
        A, v, ("%.0f" % w) if w is not None else "-",
        "correctly not a rim" if ok else "*** FALSE POSITIVE ***"))

print("\n=== ARM D: NULL, host flower-bud-alone-cpl -- MUST STAY CLEAN ===")
y2, big2, d2, v2 = base["flower-bud-alone-cpl"]
print("  nothing planted -> %s" % v2)

print("\n" + "=" * 62)
print("DETECTION FLOOR, MEASURED")
print("  narrow rim (sigma 14 px): %s" % (("%d DN" % floorA) if floorA else "NOT DETECTED at any tested amplitude"))
print("  broad  rim (sigma 40 px): %s" % (("%d DN" % floorB) if floorB else "NOT DETECTED at any tested amplitude"))
print("  gradient false positives: %d of 4 (must be 0)" % badC)
print("  null control            : %s (must be CLEAN)" % v2)
ok = (floorA is not None) and (floorB is not None) and badC == 0 and v2 == "CLEAN"
print("\nCOMMISSION %s" % ("PASSED" if ok else "FAILED -- instrument not fit to report"))
sys.exit(0 if ok else 1)
