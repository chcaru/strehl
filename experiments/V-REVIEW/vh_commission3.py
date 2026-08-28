"""COMMISSION halo3. Same four arms that failed halo2, so the comparison is fair.
  A NARROW rim sigma 14 -> must be CAUGHT, floor stated in DN
  B BROAD  rim sigma 40 -> must be CAUGHT, floor stated in DN
  C GRADIENT (the confound that produced all 4 old false positives) -> CLEAN
  D NULL -> CLEAN
Arms A/B prove it can fire; C/D prove it has not been relaxed into silence.
"""
import os, sys
import numpy as np, tifffile
from scipy.ndimage import distance_transform_edt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "ORCH-drift-check"))
import halo_profile as H, halo3

FAITH = r"C:\dev\strehl-out\ORCH-FAITHFUL\faithful"
THRESH = 200.0
AMPS = [50, 100, 200, 400, 800, 1600, 3200]


def verdict(r):
    return "HALO" if (r["overshoot"] > THRESH and
                      r["overshoot"] > 2.0 * max(r["floor"], 1.0) and r["width"] <= halo3.MAX_RIM_WIDTH and r["trough_px"] <= halo3.R - 30) else "CLEAN"


def load(stem):
    y = H.luma(tifffile.imread(os.path.join(FAITH, stem + ".tiff"))).astype(np.float32)
    ys = y[::4, ::4]; t, subj = H.segment(ys)
    big = np.repeat(np.repeat(subj, 4, 0), 4, 1)[:y.shape[0], :y.shape[1]]
    d = distance_transform_edt(~big).astype(np.float32)
    return y, big, d


fails = []
for host in ["bee-1-cpl", "bee-2-cpl"]:
    y, big, d = load(host)
    r, why = halo3.measure(y)
    assert r is not None, why
    print("\n" + "=" * 74)
    print("HOST %s   baseline overshoot %+.1f DN, noise floor %.1f -> %s" % (
        host, r["overshoot"], r["floor"], verdict(r)))
    if verdict(r) != "CLEAN":
        fails.append("%s baseline not clean" % host); print("  *** HOST NOT CLEAN ***")

    for name, d0, sg in (("NARROW sigma14 @30", 30.0, 14.0),
                         ("BROAD  sigma40 @80", 80.0, 40.0)):
        floor = None
        print("  --- ARM %s ---" % name)
        for A in AMPS:
            rim = A * np.exp(-((d - d0) ** 2) / (2 * sg ** 2)); rim[big] = 0.0
            rr, _ = halo3.measure(np.clip(y + rim, 0, 65535))
            v = verdict(rr); hit = v == "HALO"
            if hit and floor is None: floor = A
            print("      planted %5d DN -> %-6s overshoot %+8.1f  floor %6.1f  at %3.0f px %s" % (
                A, v, rr["overshoot"], rr["floor"], rr["at_px"], "CAUGHT" if hit else ""))
        print("      DETECTION FLOOR: %s" % (("%d DN" % floor) if floor else "NOT DETECTED"))
        if floor is None: fails.append("%s %s not detected" % (host, name))

    print("  --- ARM C GRADIENT (must stay CLEAN) ---")
    for A in [1000, 3000, 6000, 9000]:
        g = A * np.exp(-d / 300.0); g[big] = 0.0
        rr, _ = halo3.measure(np.clip(y + g, 0, 65535))
        v = verdict(rr); ok = v == "CLEAN"
        if not ok: fails.append("%s gradient %d false positive" % (host, A))
        print("      gradient %5d DN -> %-6s overshoot %+8.1f  %s" % (
            A, v, rr["overshoot"], "" if ok else "*** FALSE POSITIVE ***"))

print("\n" + "=" * 74)
print("ARM D NULL: every unplanted host above read CLEAN at baseline.")
print("\nCOMMISSION %s" % ("PASSED" if not fails else "FAILED"))
for f in fails: print("   FAIL: %s" % f)
sys.exit(0 if not fails else 1)

