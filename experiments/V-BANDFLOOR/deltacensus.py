r"""How big is the difference between the arms, in pixels?

The orchestrator's whole basis was "mean |delta| of 70-117 DN" on two hand
chosen crops. 70-117 DN of 65535 is 0.11-0.18 percent of full scale. This
prices that over the WHOLE frame and over the tiles the metrics actually read,
so a difference can be reported as a fraction of the range rather than as a
bare DN count that sounds large.
"""
import json, os, sys
import numpy as np
import tifffile

OUT = r"C:\dev\strehl-out\V-BANDFLOOR"

def lum(a):
    a = a.astype(np.float32)
    return 0.2126*a[...,0] + 0.7152*a[...,1] + 0.0722*a[...,2]

print("%-26s %10s %10s %10s %10s %10s %10s" % (
    "subject", "mean|d|", "p50|d|", "p99|d|", "max|d|", "mean|d|/FS", "frac>1%FS"))
for s in sys.argv[1:]:
    a = os.path.join(OUT, s + "__A-unset.tiff")
    b = os.path.join(OUT, s + "__B-coarse8.tiff")
    if not (os.path.exists(a) and os.path.exists(b)):
        print("%-26s MISSING" % s); continue
    A = tifffile.imread(a)[:, :, :3].astype(np.int32)
    B = tifffile.imread(b)[:, :, :3].astype(np.int32)
    d = np.abs(A - B)
    fs = 65535.0
    print("%-26s %10.2f %10.0f %10.0f %10.0f %9.4f%% %9.4f%%" % (
        s, d.mean(), np.percentile(d, 50), np.percentile(d, 99), d.max(),
        100*d.mean()/fs, 100*float((d > 0.01*fs).mean())))
    del A, B, d
