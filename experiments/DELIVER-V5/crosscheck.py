"""crosscheck.py -- does MY hull implementation reproduce the other lane's numbers?

V-REVIEW published, for the OLD gallery geometry (1400 px wide, 8-bit, float
resize, 26 masters x 3 channels):

    box       0.000000
    bilinear  0.000000
    bicubic   17.126
    lanczos   36.997   (median 13.424, min 1.962)

That lane's code is `experiments/V-REVIEW/vh_hull.py`.  I did not import it; I
wrote `rimlib.hull_window` from the theorem.  If two independent implementations
land on the same corpus figures, the instrument is not an artefact of either.

This is the one place DELIVER-V5 compares against somebody else's number, and it
is a comparison OF THE INSTRUMENT, not of the corpus.

Usage:  python crosscheck.py [--limit N]
"""
import os
import sys
import time

import numpy as np
import tifffile
from PIL import Image

import rimlib
from geom import masters

GALLERY_MAXW = 1400
KERNELS = {"box": Image.BOX, "bilinear": Image.BILINEAR,
           "bicubic": Image.BICUBIC, "lanczos": Image.LANCZOS}
PUBLISHED = {"box": 0.0, "bilinear": 0.0, "bicubic": 17.126, "lanczos": 36.997}
PUBLISHED_LANCZOS_MEDIAN = 13.424
PUBLISHED_LANCZOS_MIN = 1.962


def reduce_f(a8, kernel, maxw=GALLERY_MAXW):
    h, w = a8.shape
    nh = round(h * maxw / w)
    im = Image.fromarray(a8.astype(np.float32), mode="F")
    return np.asarray(im.resize((maxw, nh), KERNELS[kernel]), dtype=np.float64)


def main():
    limit = None
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])
    ms = masters()
    if limit:
        ms = ms[:limit]
    per = {k: [] for k in KERNELS}
    t0 = time.time()
    for i, (name, p) in enumerate(ms):
        a16 = tifffile.imread(p)
        a8 = rimlib.to8(a16)
        del a16
        row = {}
        for kern in KERNELS:
            worst = 0.0
            for c in range(a8.shape[2]):
                plane = np.ascontiguousarray(a8[..., c])
                out = reduce_f(plane, kern)
                exc, dfc = rimlib.hull_window(plane, out, support=18)
                worst = max(worst, float(np.maximum(exc, dfc).max()))
            row[kern] = worst
            per[kern].append(worst)
        print("%2d/%2d %-38s %s" % (i + 1, len(ms), name,
              "  ".join("%s %8.4f" % (k, row[k]) for k in KERNELS)), flush=True)
        del a8
    dt = time.time() - t0

    print("\n=== corpus summary, %d masters, %.1f s ===" % (len(ms), dt))
    print("%-10s %10s %10s %10s   %10s" % ("kernel", "max", "median", "min", "published max"))
    ok = 0
    checks = 0
    for k in KERNELS:
        v = np.array(per[k])
        print("%-10s %10.4f %10.4f %10.4f   %10.3f"
              % (k, v.max(), np.median(v), v.min(), PUBLISHED[k]))
    if limit is None:
        tol = 0.05
        for k in KERNELS:
            v = np.array(per[k])
            checks += 1
            got, want = v.max(), PUBLISHED[k]
            good = abs(got - want) <= max(tol, 0.01 * want)
            ok += 1 if good else 0
            print("  [%s] %-9s max %.4f vs published %.3f"
                  % ("PASS" if good else "FAIL", k, got, want))
        v = np.array(per["lanczos"])
        for label, got, want in (("median", float(np.median(v)), PUBLISHED_LANCZOS_MEDIAN),
                                 ("min", float(v.min()), PUBLISHED_LANCZOS_MIN)):
            checks += 1
            good = abs(got - want) <= max(0.05, 0.01 * want)
            ok += 1 if good else 0
            print("  [%s] lanczos %-6s %.4f vs published %.3f"
                  % ("PASS" if good else "FAIL", label, got, want))
        print("\n  agreement: %d pass + %d fail = %d of %d"
              % (ok, checks - ok, checks, checks))
        print("\nVERDICT: %s" % (
            "two independent implementations agree; the instrument is not an "
            "artefact of either" if ok == checks else
            "DISAGREEMENT -- one of the two implementations is wrong and it "
            "must be resolved before any DELIVER-V5 number is trusted"))
        return 0 if ok == checks else 1
    print("\n(--limit set: no agreement verdict, this was a smoke run)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
