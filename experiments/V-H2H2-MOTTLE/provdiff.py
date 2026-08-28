# provenance.ps1 compares SHA-256 of two renders and prints DIFFER.  That is the
# right default -- but "DIFFER" is a single bit, and a single bit cannot tell me
# whether my numbers are void or whether they hold to nine decimal places.  The
# two files differ by 11 bytes out of 197,798,934, and both logs report the same
# backend, the same alignment reference and the same 19 frames placed, so the
# difference may be entirely in the TIFF header.
#
# This measures the drift in the units my conclusions are actually stated in:
# per-pixel DN, band energy in the three bands of section 13, and the coherence
# statistic itself.  If gamma(mine, pin) is 1.0 in every band then the drift
# cannot have produced any effect I reported, because the effects I reported are
# gamma differences of order 0.5.
#
# The comparison is a NEGATIVE control by construction: the two renders share a
# frame set, so section 12's displacement confound is absent and any difference
# here is attributable to the binary alone.

import io
import json
import os
import sys

import numpy as np
import tifffile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from decomplib import bandpass  # noqa: E402
from coh import gamma  # noqa: E402

PROV = r"C:\dev\strehl-out\V-H2H2\ladder\prov"
BANDS = {"5-15": (5, 15), "20-60": (20, 60), "40-120": (40, 120)}


def main():
    a = tifffile.imread(os.path.join(PROV, "mine.tiff")).astype(np.float64)
    b = tifffile.imread(os.path.join(PROV, "pin.tiff")).astype(np.float64)
    print("shapes  mine %s  pin %s" % (a.shape, b.shape))
    if a.shape != b.shape:
        sys.exit("SHAPES DIFFER -- the drift changed the output geometry")

    d = a - b
    n_diff = int(np.count_nonzero(d))
    rms_d = float(np.sqrt(np.mean(d * d)))
    rms_a = float(np.sqrt(np.mean(a * a)))
    sa = os.path.getsize(os.path.join(PROV, "mine.tiff"))
    sb = os.path.getsize(os.path.join(PROV, "pin.tiff"))
    rec = {"pixel_identical": n_diff == 0, "n_diff": n_diff, "n_px": int(d.size),
           "pct_diff": 100.0 * n_diff / d.size, "max_abs": float(np.abs(d).max()),
           "rms_diff": rms_d, "image_rms": rms_a, "drift_frac_pct": 100.0 * rms_d / rms_a,
           "size_mine": sa, "size_pin": sb, "size_delta": sa - sb}
    print("pixels differing        : %d of %d (%.6f%%)"
          % (n_diff, d.size, rec["pct_diff"]))
    print("max |difference|        : %.6g DN" % rec["max_abs"])
    print("rms  difference         : %.6g DN" % rms_d)
    print("image rms               : %.6g DN" % rms_a)
    print("drift as fraction       : %.4f%%" % rec["drift_frac_pct"])

    # the raw byte difference, for the record: 11 bytes of a 197 MB file is a
    # header string, not an image
    print("file sizes              : %d vs %d (%d bytes apart)" % (sa, sb, sa - sb))

    if n_diff == 0:
        print("\nPIXEL-IDENTICAL -- the SHA-256 difference is metadata only.")
        print("Every measurement in sections 12 and 13 is a statement about the")
        print("shipping merge.")
        json.dump(rec, io.open(os.path.join(PROV, "provdiff.json"), "w"))
        return 0

    # not identical: quantify in the bands the conclusions are stated in
    g = a[..., 1] if a.ndim == 3 else a
    h = b[..., 1] if b.ndim == 3 else b
    # a central crop, big enough for the coarsest band, cheap enough to run
    cy, cx = g.shape[0] // 2, g.shape[1] // 2
    r = 768
    g = g[cy - r:cy + r, cx - r:cx + r]
    h = h[cy - r:cy + r, cx - r:cx + r]
    rows = {}
    for name, (lo, hi) in BANDS.items():
        ea = float(np.sqrt(np.mean(bandpass(g, lo, hi) ** 2)))
        eb = float(np.sqrt(np.mean(bandpass(h, lo, hi) ** 2)))
        gm = gamma(g, h, lo, hi)
        rows[name] = {"mine": ea, "pin": eb, "ratio": ea / eb, "gamma": gm}
        print("band %-7s  mine %.6f  pin %.6f  ratio %.6f  gamma %.9f"
              % (name, ea, eb, ea / eb, gm))
    json.dump(dict(rec, bands=rows), io.open(os.path.join(PROV, "provdiff.json"), "w"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
