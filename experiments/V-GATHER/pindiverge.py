r"""Do the two sealed pins differ on ANY subject?

Three probes have now failed to separate 740e7056 from 9b05d0b7, so before I say
anything about the unsealed stray I need to know whether these builds differ at
all in output. If they do not, my probes are not insensitive -- there is simply
nothing to detect, and "which pin rendered this" stops being a question about
pixels. If they do differ on some subject, then my two-subject probe is merely
too narrow and the stray claim stays unsupported for a different reason.

Compare the shipped masters directly: SHIP-V3 vs SHIP-V4, same subject, both
rendered by the harness with the same switch state.
"""
import os
import numpy as np
import tifffile

V3D = r"C:\dev\strehl-out\acceptance\SHIP-V3"
V4D = r"C:\dev\strehl-out\acceptance\SHIP-V4"


def subjects(d, tag):
    out = {}
    for f in os.listdir(d):
        if f.endswith(".tiff"):
            out[f[:-len("--%s.tiff" % tag)]] = os.path.join(d, f)
    return out


a, b = subjects(V3D, "SHIP-V3"), subjects(V4D, "SHIP-V4")
both = sorted(set(a) & set(b))
print("subjects sealed by both corpora: %d" % len(both))
print("%-26s %14s %10s %8s" % ("subject", "differing px", "max DN", "% px"))
print("-" * 64)
nsame = ndiff = nskip = 0
for s in both:
    try:
        x = tifffile.imread(a[s])[..., :3].astype(np.int32)
        y = tifffile.imread(b[s])[..., :3].astype(np.int32)
    except Exception as e:
        print("%-26s  SKIP %s" % (s, type(e).__name__)); nskip += 1; continue
    if x.shape != y.shape:
        print("%-26s  SHAPE %s vs %s" % (s, x.shape, y.shape)); ndiff += 1; continue
    d = np.abs(x - y)
    n = int((d > 0).sum())
    if n:
        ndiff += 1
    else:
        nsame += 1
    print("%-26s %8d/%d %10d %7.2f%%" % (s, n, d.size, d.max(), 100.0 * n / d.size))

print("\nPARTITION  identical %d + differing %d + skipped %d = %d of %d"
      % (nsame, ndiff, nskip, nsame + ndiff + nskip, len(both)))
if ndiff == 0:
    print("\nThe two sealed pins produce BIT-IDENTICAL masters on every shared")
    print("subject. They are distinct binaries with indistinguishable output on")
    print("this corpus, which is why no probe of mine could separate them.")
else:
    print("\nThe pins DO differ on %d subject(s); my two-subject probe was simply")
    print("too narrow to see it, and the stray claim stays unsupported." % ndiff)
