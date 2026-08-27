r"""Is "the stray reproduces the shipping pin" a real result or a trivially
satisfiable one?

The stray matched 9b05d0b7 pixel-for-pixel on both gather arms. But 740e7056 and
9b05d0b7 differ chiefly in the DEFAULT of STREHL_FULLRES_GATHER, and I drove that
flag explicitly. If setting the flag erases the difference between the two SEALED
pins as well, then "matches 9b05d0b7 under explicit flags" is a property every
build in the tree would have, and it says nothing about the stray.

So run the discriminator: same subject, same explicit flags, V3 pin vs V4 pin.
"""
import itertools
import numpy as np
import tifffile

D = r"C:\dev\strehl-out\V-GATHER\strayprobe"
L = {}
for arm in ("pin", "stray", "v3"):
    for g in ("0", "1"):
        L[(arm, g)] = tifffile.imread(r"%s\cb-%s-g%s.tiff" % (D, arm, g))[..., :3]

NAME = {"pin": "9b05d0b7 (seals SHIP-V4)", "stray": "F663B703 (unsealed)",
        "v3": "740e7056 (seals SHIP-V3)"}


def cmp(a, b, g):
    x, y = L[(a, g)].astype(np.int32), L[(b, g)].astype(np.int32)
    d = np.abs(x - y)
    return int((d > 0).sum()), int(d.max()), d.size


print("%-30s %-30s %4s %14s %10s" % ("A", "B", "flag", "differing px", "max DN"))
print("-" * 94)
for (a, b), g in itertools.product((("pin", "stray"), ("pin", "v3"), ("stray", "v3")),
                                   ("0", "1")):
    n, m, t = cmp(a, b, g)
    print("%-30s %-30s   =%s %9d/%d %10d" % (NAME[a], NAME[b], g, n, t, m))

n0, _, _ = cmp("pin", "v3", "0")
n1, _, _ = cmp("pin", "v3", "1")
ns, _, _ = cmp("pin", "stray", "0")
print()
if n0 == 0 and n1 == 0:
    print("DISCRIMINATOR FAILED: the two SEALED pins are themselves identical")
    print("under explicit flags, so 'stray matches 9b05d0b7' is a property every")
    print("build would show. The stray equivalence claim is NOT supported.")
else:
    print("DISCRIMINATOR HOLDS: the two sealed pins DIFFER under the same explicit")
    print("flags (%d and %d pixels), so the probe can tell two builds apart." % (n0, n1))
    print("The stray's %d-pixel agreement with 9b05d0b7 is therefore a real" % ns)
    print("measurement of equivalence on this path, not an artifact of the flags.")
