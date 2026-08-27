r"""The equivalence claim, retested where the pins are actually allowed to differ.

Under EXPLICIT STREHL_FULLRES_GATHER all three builds agreed, including the two
sealed pins -- so that comparison could not tell any two builds apart and the
stray's agreement there was worth nothing. Rerun at DEFAULT flags, which is what
the shipping harness uses and where 740e7056 and 9b05d0b7 are known to sit on
opposite sides of at least one decision.
"""
import itertools
import numpy as np
import tifffile

D = r"C:\dev\strehl-out\V-GATHER\strayprobe"
NAME = {"pin": "9b05d0b7 (seals SHIP-V4)", "stray": "F663B703 (unsealed)",
        "v3": "740e7056 (seals SHIP-V3)"}
L = {a: tifffile.imread(r"%s\cb-%s-def.tiff" % (D, a))[..., :3].astype(np.int32)
     for a in NAME}

res = {}
print("%-30s %-30s %14s %10s" % ("A", "B", "differing px", "max DN"))
print("-" * 88)
for a, b in itertools.combinations(NAME, 2):
    d = np.abs(L[a] - L[b])
    res[(a, b)] = (int((d > 0).sum()), int(d.max()))
    print("%-30s %-30s %8d/%d %10d" % (NAME[a], NAME[b], res[(a, b)][0], d.size,
                                       res[(a, b)][1]))

sealed = res[("pin", "v3")][0]
stray = res[("pin", "stray")][0]
print()
if sealed == 0:
    print("STILL NOT DISCRIMINATING: the two sealed pins are identical at default")
    print("flags too on this subject, so this probe cannot distinguish builds and")
    print("the stray's agreement remains uninformative. NOT SUPPORTED.")
else:
    print("DISCRIMINATING: the two sealed pins differ at default flags by %d px."
          % sealed)
    if stray == 0:
        print("The stray agrees with 9b05d0b7 exactly (%d px) on a probe that CAN"
              % stray)
        print("separate builds. Equivalence SUPPORTED on this subject and path.")
    else:
        print("The stray differs from 9b05d0b7 by %d px. NOT equivalent." % stray)
