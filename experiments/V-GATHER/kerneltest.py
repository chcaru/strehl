r"""Is the edge overshoot produced by the WARP KERNEL?

catmull-rom, the shipped default resampler, has NEGATIVE LOBES. A kernel with
negative lobes produces overshoot at a step by construction. nearest has no
negative lobes and CANNOT ring. If the overshoot is a property of the warp, it
must fall when the kernel is swapped and everything else is held fixed.

Both arms come from the SAME sealed binary in the same invocation shape, on a
LINEAR gauge (--linear-srgb --demosaic), so no per-image tone fit can distort
the edge profile being measured. Sites are selected once, on a rim-free
reference built from the shipped arm, and both arms are measured at those same
sites -- otherwise the two arms are scored over different edge populations.
"""
import os
import subprocess
import sys
import time

import numpy as np
import tifffile
from scipy.ndimage import gaussian_filter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import certmeasure as cm
import rimindep as RI

OUTDIR = r"C:\dev\strehl-out\V-GATHER\kernel"
KERNELS = ["catmull-rom", "nearest", "lanczos3"]


def render(subject, kernel, path):
    env = dict(os.environ)
    env["STREHL_CACHE_DIR"] = os.path.join(cm.WORK, subject, "cache")
    os.makedirs(env["STREHL_CACHE_DIR"], exist_ok=True)
    for v in ("STREHL_FIX_CA", "STREHL_EDGE_AWARE", "STREHL_EDGE_TAU",
              "STREHL_EDGE_CONF", "STREHL_ONLY_FRAME"):
        env.pop(v, None)
    cmd = [cm.EXE, "stack", os.path.join(cm.RAW, subject), "--out", path,
           "--linear-srgb", "--demosaic", "--resampler", kernel]
    t = time.time()
    p = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if p.returncode != 0 or not os.path.exists(path):
        raise SystemExit("render failed (%s, %s): %s"
                         % (subject, kernel, p.stderr[-400:]))
    return time.time() - t


def main():
    cm.check_binary()
    os.makedirs(OUTDIR, exist_ok=True)
    subject = sys.argv[1]
    imgs = {}
    for k in KERNELS:
        p = os.path.join(OUTDIR, "%s--%s.tiff" % (subject, k))
        if not os.path.exists(p):
            dt = render(subject, k, p)
            print("  rendered %-12s in %.0fs" % (k, dt))
            sys.stdout.flush()
        rgb, lat = cm.read_rgb(p)
        imgs[k] = RI.luma(rgb)
        print("  %-12s lattice %s" % (k, lat))

    ref = gaussian_filter(imgs["catmull-rom"], 2.0)

    # MINSTEP must be DERIVED on this gauge, not inherited. It was calibrated on
    # tone-mapped output; linear light puts the same visual edge at a far lower
    # normalised amplitude, and the inherited 0.10 selected ZERO sites here --
    # after which the script still printed a conclusion, from n=0. A threshold
    # carried across a gauge change is the same defect as a ratio carried across
    # one.
    g = imgs["catmull-rom"]
    rows = np.arange(200, g.shape[0] - 200, 37)
    grad = np.abs(np.diff(g[rows], axis=1))
    RI.MINSTEP = float(np.percentile(grad, 99.5))
    print("\nMINSTEP derived on this gauge: %.4f (99.5th pct of |grad|)"
          % RI.MINSTEP)

    sites = RI.select(ref)
    print("%d edge sites, frozen, measured identically on every arm" % len(sites))
    if len(sites) < 50:
        raise SystemExit("ONLY %d SITES -- this instrument has no reach on this "
                         "image and any number it prints would be noise. Refusing "
                         "to report a kernel comparison." % len(sites))
    nullv, nulln = RI.overshoot(RI.profiles(ref, sites))
    if nulln < 50 or nullv != nullv:
        raise SystemExit("NULL CONTROL UNUSABLE (n=%d, value=%r) -- without a "
                         "floor the arms cannot be corrected and nothing here "
                         "may be reported." % (nulln, nullv))
    print("null (blurred shipped arm): %+.2f%%   <- the instrument floor\n" % (100 * nullv))
    print("  %-12s %10s %12s" % ("kernel", "overshoot", "corrected"))
    base = None
    for k in KERNELS:
        v, n = RI.overshoot(RI.profiles(imgs[k], sites))
        if n < 50 or v != v:
            raise SystemExit("ARM %s UNUSABLE (n=%d) -- refusing to compare" % (k, n))
        c = v - nullv
        if k == "catmull-rom":
            base = c
        print("  %-12s %+9.2f%% %+11.2f%%   n=%d" % (k, 100 * v, 100 * c, n))
    print()
    vn, _ = RI.overshoot(RI.profiles(imgs["nearest"], sites))
    dn = (vn - nullv) - base
    print("nearest minus catmull-rom: %+.2f points" % (100 * dn))
    if dn < -0.01:
        print("The overshoot FALLS when the kernel loses its negative lobes, so\n"
              "the warp resampler is implicated in it.")
    elif dn > 0.01:
        print("The overshoot RISES with nearest, so the kernel's negative lobes\n"
              "are NOT the source; something else in the pipeline makes it.")
    else:
        print("No resolvable difference between kernels; the kernel is not the\n"
              "source, or this instrument cannot separate them here.")


if __name__ == "__main__":
    main()
