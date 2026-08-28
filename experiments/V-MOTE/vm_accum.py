"""V-MOTE P1 -- accumulate the flat-field quad mean, split three ways.

Reuses the arithmetic of `crates/strehl-cli/examples/defect-flat-census.rs`
(quad_mean over the FULL raw buffer with active origin (0,0), per-frame
normalisation by the frame's own median, EXPOSURE_WINDOW (0.06, 0.90)) and the
block split of `defect-cpl-split.rs` (BLOCK2_FIRST = DSC00263).  It writes
nothing but .npy caches; every number is printed.

The one deliberate difference from the census: NO box-mean high pass is applied
here.  The high pass is the step that is suspect within 64 quads of an edge, so
this file stops before it and leaves the background model to vm_depth.py.
"""
import os, sys, glob
import numpy as np
import rawpy

FLATS = r"D:\personal\macro\flat-fields\flat-fields"
OUT   = r"C:\dev\strehl-out\V-MOTE\cache"
BLOCK2_FIRST = "DSC00263"
EXPOSURE_WINDOW = (0.06, 0.90)
BLACK, WHITE = 512.0, 16383.0
QH, QW = 2344, 3520


def main():
    os.makedirs(OUT, exist_ok=True)
    files = sorted(glob.glob(os.path.join(FLATS, "*.ARW")))
    print("files: %d" % len(files))
    acc = {k: np.zeros((QH, QW), np.float64) for k in ("odd", "even", "b1", "b2")}
    n   = {k: 0 for k in acc}
    rej = 0
    for i, f in enumerate(files):
        with rawpy.imread(f) as r:
            a = r.raw_image.astype(np.float32)
        q = a.reshape(QH, 2, QW, 2).mean(axis=(1, 3)) - BLACK
        med = float(np.median(q[::8, ::8]))          # census subsampling, 8x8
        level = med / (WHITE - BLACK)
        if not (EXPOSURE_WINDOW[0] <= level <= EXPOSURE_WINDOW[1]):
            rej += 1
            continue
        nq = q / med
        half = "odd" if (i % 2) else "even"
        acc[half] += nq; n[half] += 1
        blk = "b2" if os.path.basename(f)[:8] >= BLOCK2_FIRST else "b1"
        acc[blk] += nq; n[blk] += 1
        if (i + 1) % 60 == 0:
            print("  %d/%d" % (i + 1, len(files)), flush=True)
    print("used odd %d even %d | b1 %d b2 %d | rejected %d | examined %d"
          % (n["odd"], n["even"], n["b1"], n["b2"], rej, len(files)))
    assert n["odd"] + n["even"] + rej == len(files)
    assert n["b1"] + n["b2"] + rej == len(files)
    for k in acc:
        np.save(os.path.join(OUT, "flat_%s.npy" % k), (acc[k] / max(n[k], 1)).astype(np.float32))
    allf = (acc["odd"] + acc["even"]) / (n["odd"] + n["even"])
    np.save(os.path.join(OUT, "flat_all.npy"), allf.astype(np.float32))
    print("wrote %s" % OUT)
    print("mean field: min %.5f  median %.5f  max %.5f"
          % (allf.min(), np.median(allf), allf.max()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
