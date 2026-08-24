"""S8 — diagnose the N2 failure properly. My first diagnosis was wrong.

WHAT I GOT WRONG
----------------
S6's N2 control demanded that output green be bit-identical between the two
renders, on the grounds that the co-siting fix does not touch green. It failed.
I blamed the pinned binary predating M86's alignment work, built a control
binary from the current tree (S7), and it failed again with the SAME diff
magnitudes to the digit -- which is the signature of a hypothesis that was never
the cause.

The actual cause is in the code I wrote, and it is not a defect. Under `--srgb`
`develop_pixel` applies the camera-to-sRGB matrix, and that matrix MIXES
channels:

    G_out = m[1][0]*R_lin + m[1][1]*G_lin + m[1][2]*B_lin

So changing red and blue must change output green. Green is untouched as an
INPUT, which is what the Rust unit test asserts and what it can assert because
it runs with no matrix. It cannot be untouched as an OUTPUT once a matrix is in
the path. N2 as written was a claim about the wrong quantity.

THE CORRECTED CONTROL
---------------------
N2' is conditional and it is the claim I can actually defend: on pixels where
red and blue did NOT change, green must not change either. If green carried an
independent change -- a stray blur, an off-by-one, anything -- it would show
there, because on those pixels the matrix has nothing new to mix in.

Its power control is that the same pixels must exist in quantity and the
unconditional green difference must be large, or N2' is vacuously true.

C13 additionally settles whether the pin and the current tree render this
configuration identically, which is what S7 was built to find out.
"""

import hashlib
import os
import sys

import numpy as np
import tifffile

OUT = r"C:\dev\strehl-out\M95-chroma-cositing"


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    print("== C13: did the pin and the current tree render this config the same? ==")
    a = sha256(os.path.join(OUT, "ship-before.tif"))
    b = sha256(os.path.join(OUT, "ship-before-Z.tif"))
    print("   pin, align on, gate 2.0        : %s" % a)
    print("   this tree with co-siting off   : %s" % b)
    print("   C13: %s" % (
        "identical -- M86's work has NOT changed this render, so my first "
        "diagnosis of the N2 failure was wrong" if a == b else
        "different -- the tree HAS moved, so the pin was indeed unusable as a before"))

    z = tifffile.imread(os.path.join(OUT, "ship-before-Z.tif")).astype(np.int32)
    y = tifffile.imread(os.path.join(OUT, "ship-after.tif")).astype(np.int32)

    dR = z[:, :, 0] - y[:, :, 0]
    dG = z[:, :, 1] - y[:, :, 1]
    dB = z[:, :, 2] - y[:, :, 2]
    n = dG.size

    print("\n== power control: is there anything for N2' to detect? ==")
    print("   pixels where green differs at all : %d of %d (%.2f%%)"
          % (int((dG != 0).sum()), n, 100 * (dG != 0).mean()))
    print("   max |dG| over the whole frame     : %d DN" % int(np.abs(dG).max()))

    unchanged = (dR == 0) & (dB == 0)
    k = int(unchanged.sum())
    print("\n== N2': green on pixels where red and blue did NOT change ==")
    print("   qualifying pixels : %d of %d (%.2f%%)" % (k, n, 100 * k / n))
    if k < 10000:
        print("   N2': VACUOUS -- too few qualifying pixels to be a test")
        return 1
    gsub = dG[unchanged]
    bad = int((gsub != 0).sum())
    print("   of those, green differs on : %d (%.4f%%)" % (bad, 100 * bad / k))
    print("   max |dG| on those pixels   : %d DN" % int(np.abs(gsub).max()))
    n2 = bad == 0
    print("   N2': %s" % ("PASS - green carries no independent change"
                          if n2 else "FAIL - green moved on its own"))

    print("\n== is the green change explained by the matrix, quantitatively? ==")
    both = (dR != 0) | (dB != 0)
    corr = float(np.corrcoef(
        np.stack([dG[both][::37].astype(float),
                  dR[both][::37].astype(float),
                  dB[both][::37].astype(float)]))[0, 1:].max())
    print("   max |corr(dG, dR or dB)| on changed pixels: %.4f" % corr)
    print("   (a matrix-mediated change is strongly correlated with its cause;")
    print("    an independent defect in green would not be)")

    ok = n2
    print("\nS8: %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
