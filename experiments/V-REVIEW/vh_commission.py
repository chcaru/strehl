"""Commission the extended halo instrument: null, planted halo, detection floor.

A checker whose sensitivity is unmeasured is not evidence.  Three arms:

  NULL      plant nothing.  The verdict must not move.  Without this a
            detector that fires on everything would score perfectly below.
  PLANT     add a rim of KNOWN amplitude at a KNOWN radius into a subject that
            reads clean.  The instrument must catch it.
  FLOOR     sweep amplitude x radius and report the smallest amplitude caught
            at each radius.  The floor is expected to DEPEND ON RADIUS: close
            to the silhouette the subject's own penumbra rises thousands of DN
            per band, so a rim there rides a gradient larger than itself.  That
            is a property of any radial-profile detector and the honest output
            is the floor as a function of radius, not one number.

Every plant is verified to have landed -- amplitude actually present in the
pixels -- and hard-errors if not.  A plant that silently fails to apply would
produce a "not detected" that means nothing.
"""
import os, sys
import numpy as np, tifffile
from scipy.ndimage import distance_transform_edt

sys.path.insert(0, r"C:\dev\blog\death-of-software\projects\strehl\experiments\ORCH-drift-check")
import halo_profile as H

SRC = r"C:\dev\strehl-out\ORCH-FAITHFUL\faithful"
THRESH = 200.0
RADII = [8, 15, 30, 60, 100]
AMPS = [100, 200, 400, 800, 1600, 3200, 6400, 12800]
SUBJECTS = ["bee-2-cpl", "flower-bud-alone-cpl", "109MSDCF"]


def load(stem):
    for e in (".tiff", ".tif"):
        p = os.path.join(SRC, stem + e)
        if os.path.exists(p):
            return H.luma(tifffile.imread(p))
    raise SystemExit("missing subject %s" % stem)


def dfull(y):
    """Distance from the silhouette on the instrument's own grid, expanded to
    full resolution so a rim can be planted in the real image."""
    ys = y[::4, ::4]
    _, subj = H.segment(ys)
    d = distance_transform_edt(~subj) * 4
    d = np.repeat(np.repeat(d, 4, 0), 4, 1)
    return d[:y.shape[0], :y.shape[1]], np.repeat(
        np.repeat(subj, 4, 0), 4, 1)[:y.shape[0], :y.shape[1]]


def plant(y, d, subj, amp, rad, width=8.0):
    g = np.exp(-((d - rad) ** 2) / (2.0 * width ** 2))
    g[subj] = 0.0
    out = y + amp * g
    landed = float((out - y).max())
    if amp > 0 and landed < 0.5 * amp:
        raise SystemExit("PLANT DID NOT LAND: asked %g, max delta %.1f" % (amp, landed))
    if amp == 0 and landed != 0.0:
        raise SystemExit("NULL ARM IS NOT NULL: max delta %.1f" % landed)
    return out, landed


def verdict(y):
    v, over, bump, pen, fl, bands, why = H.profile(y)
    if v != "MEASURED":
        return v, None, None
    return ("HALO" if (over > THRESH or bump > THRESH) else "clean"), over, bump


def main():
    print("=" * 96)
    print("ARM 1/2: NULL -- plant nothing, verdict must not move")
    print("=" * 96)
    base = {}
    bad = 0
    for s in SUBJECTS:
        y = load(s)
        d, subj = dfull(y)
        v0, o0, b0 = verdict(y)
        yn, landed = plant(y, d, subj, 0, 15)
        v1, o1, b1 = verdict(yn)
        ok = (v0 == v1) and (o0 == o1) and (b0 == b1)
        bad += 0 if ok else 1
        print("  %-24s %-6s over %+9.1f bump %7.1f  -> null %-6s over %+9.1f  %s"
              % (s, v0, o0, b0, v1, o1, "OK" if ok else "*** MOVED ***"))
        base[s] = (y, d, subj, v0, o0, b0)

    print()
    print("=" * 96)
    print("ARM 2/2: PLANTED HALO -- detection floor in DN, by radius")
    print("=" * 96)
    for s in SUBJECTS:
        y, d, subj, v0, o0, b0 = base[s]
        print("\n%s   baseline %s  overshoot %+.1f  bump %.1f" % (s, v0, o0, b0))
        print("  %8s %12s %12s  %s" % ("radius", "floor(DN)", "at floor", "sweep"))
        for r in RADII:
            floor = None
            marks = []
            for a in AMPS:
                yp, _ = plant(y, d, subj, a, r)
                v, o, b = verdict(yp)
                hit = (v == "HALO")
                marks.append("%d%s" % (a, "+" if hit else "-"))
                if hit and floor is None:
                    floor = (a, o, b)
                    break
            if floor:
                print("  %8d %12d %12s  %s"
                      % (r, floor[0], "over %+.0f bump %.0f" % (floor[1], floor[2]),
                         " ".join(marks)))
            else:
                print("  %8d %12s %12s  %s"
                      % (r, "NOT CAUGHT", "-", " ".join(marks)))

    print()
    print("=" * 96)
    print("NULL ARMS THAT MOVED: %d (must be 0)" % bad)
    print("=" * 96)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
