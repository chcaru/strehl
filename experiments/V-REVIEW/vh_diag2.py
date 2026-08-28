"""Follow-ups the first diagnostic raised.

(1) 112/113MSDCF report "far field only 0 px".  Is there NO distant background,
    or is the FIXED 400-900 px window simply beyond this subject's reach?
    dmax answers it.
(2) REGIME GUARD 2 needs both far annuli >200 px or it does not apply at all.
    A guard that silently does not apply reads exactly like a guard that
    passed.  flat-on-ruler-cpl -- the very subject the guard was written for --
    printed spread "-" and was measured anyway.  Count where it is inert.
(3) For the multi-component skips, are the major parts spatially separated
    (tweezers' two arms, a real confound) or one dominant blob with satellites?
"""
import glob, json, os, sys
import numpy as np, tifffile
from scipy.ndimage import (binary_closing, binary_opening, center_of_mass,
                           distance_transform_edt, label)

sys.path.insert(0, r"C:\dev\blog\death-of-software\projects\strehl\experiments\ORCH-drift-check")
import halo_profile as H
CACHE = r"D:\strehl-out\V-REVIEW\halo\cache"


def main():
    rows = []
    for f in sorted(glob.glob(os.path.join(CACHE, "*.npy"))):
        stem = os.path.basename(f)[:-4]
        y = np.load(f)[::2, ::2]
        t = H.otsu(y.ravel())
        subj = binary_opening(y < t, np.ones((3, 3)))
        subj = binary_closing(subj, np.ones((5, 5)))
        d = distance_transform_edt(~subj) * 4
        lab, nlab = label(subj)
        sizes = np.bincount(lab.ravel())[1:]
        tot = float(sizes.sum()); dom = int(np.argmax(sizes)) + 1
        mid = (H.FAR[0] + H.FAR[1]) // 2
        a1 = int(((d >= H.FAR[0]) & (d < mid)).sum())
        a2 = int(((d >= mid) & (d < H.FAR[1])).sum())
        # separation of the major parts, in units of the dominant part's radius
        maj = [i + 1 for i, s in enumerate(sizes) if s >= 0.01 * tot]
        sep = None
        if len(maj) > 1:
            cs = np.array([center_of_mass(lab == m) for m in maj]) * 4
            c0 = np.array(center_of_mass(lab == dom)) * 4
            rad = float(np.sqrt(sizes[dom - 1] * 16 / np.pi))
            sep = float(max(np.hypot(*(c - c0)) for c in cs)) / rad
        rows.append((stem, float(d.max()), a1, a2, len(maj), sep,
                     float(sizes.max()) / tot))
    print("%-38s %7s %9s %9s %6s %8s %7s  %s"
          % ("subject", "dmax", "annulus1", "annulus2", "major", "sep/rad",
             "large", "guard2 status"))
    print("-" * 118)
    inert = 0
    for stem, dmax, a1, a2, nmaj, sep, large in rows:
        ok = a1 > 200 and a2 > 200
        if not ok:
            inert += 1
        print("%-38s %7.0f %9d %9d %6d %8s %6.0f%%  %s"
              % (stem, dmax, a1, a2, nmaj,
                 "-" if sep is None else "%.2f" % sep, large * 100,
                 "applies" if ok else "*** INERT (needs both >200) ***"))
    print("-" * 118)
    print("REGIME GUARD 2 is inert on %d of %d subjects." % (inert, len(rows)))
    print("dmax < 400 means the fixed FAR window (400-900 px) is unreachable")
    print("for that subject -- the background exists but is never that distant.")


if __name__ == "__main__":
    main()
