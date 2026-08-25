"""R18 -- re-derive camera_to_srgb independently, then forward-model its damage.

ORCH reports the corpus quoted `rownorm(inv(A@S))` where the crate computes
`inv(rownorm(A@S))`, swapping the green->red and red->green leaks. Per ORCH's
own instruction -- "if a constant you use is also computed by the crate, read
the crate's own statement of it before you trust the corpus" -- this script
does not take either the corpus value or ORCH's correction on trust. It
recomputes both orderings from the crate's own constants:

    SRGB_TO_XYZ_D65   color.rs:79-83
    A7C2_XYZ_TO_CAM   color.rs:812-816
    order of ops      color.rs:180-208  (step 2 row-normalise, step 3 invert)

and adjudicates against an artefact rather than a fact number: the doc comment
at color.rs:221, which states the green row as [-0.115, +1.489, -0.374].

Then it does something neither the corpus nor the correction has done. ORCH
wrote that the matrix and the demosaic are confounded in an sRGB render and
that "no internal consistency check could have separated them". That is true
of a check applied to the finished render. It is NOT true of a FORWARD MODEL:
the binned linear space has no demosaic in it at all, so applying the matrix
alone to clean data isolates the matrix's contribution exactly.

BARS -- registered before running.

  E1  ADJUDICATION.  The crate's order (normalise-then-invert) reproduces
      color.rs:221's green row to 3 d.p. and the corpus order
      (invert-then-normalise) does not.
      Falsified if the corpus ordering matches instead, or if neither does --
      either of which would mean ORCH's correction is itself wrong and I must
      say so rather than agree.

  E2  MAGNITUDES.  Registered from ORCH's message so the comparison is
      honest: green-in-red 27.4%, red-in-green 7.7%.  Falsified if my
      independent computation differs from either by more than 0.5 points.

  E3  FORWARD MODEL.  Applying the corrected matrix to the CLEAN r13 data,
      with the R16 support floor of 120 held fixed, degrades the transfer
      check away from its clean value of 0.9148 by more than 5%.
      Falsified if the degradation is under 5% -- which would mean the matrix
      alone does NOT account for the sRGB contamination and the demosaic must
      carry most of it.  Either outcome is a result: this bar apportions
      blame between the two confounded operators, it does not merely confirm.

  E4  DIRECTION.  Registered: the leak biases the estimate TOWARD ZERO
      (attenuation), because mixing the reference channel into the tracked
      channel pulls the tracked channel's apparent position toward the
      reference.  Falsified if the transfer check moves AWAY from zero.
"""

import os
import sys

import numpy as np
import tifffile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from r13_clean_calib import EPS, R13  # noqa: E402
from r15_reconcile import estimate_floored  # noqa: E402

# color.rs:79-83
S = np.array([[0.4124564, 0.3575761, 0.1804375],
              [0.2126729, 0.7151522, 0.0721750],
              [0.0193339, 0.1191920, 0.9503041]])
# color.rs:812-816
A = np.array([[0.7460, -0.2365, -0.0588],
              [-0.5687, 1.3442, 0.2474],
              [-0.0624, 0.1156, 0.6584]])
DOC_GREEN = np.array([-0.115, 1.489, -0.374])  # color.rs:221
FLOOR = 120.0
CLEAN_TRANSFER = 0.9148  # section 25, R16 Z1


def rownorm(m):
    return m / m.sum(axis=1, keepdims=True)


def main():
    print("=" * 76)
    print("R18 -- camera_to_srgb re-derived from the crate, then forward-modelled")
    print("=" * 76)

    crate = np.linalg.inv(rownorm(A @ S))      # color.rs: normalise then invert
    corpus = rownorm(np.linalg.inv(A @ S))     # what the corpus quoted

    print("\nE1  ADJUDICATION against color.rs:221's own doc comment")
    print(f"    doc comment green row        {DOC_GREEN}")
    print(f"    crate order  (norm->inv)     {np.round(crate[1], 6)}")
    print(f"    corpus order (inv->norm)     {np.round(corpus[1], 6)}")
    d_crate = float(np.abs(crate[1] - DOC_GREEN).max())
    d_corpus = float(np.abs(corpus[1] - DOC_GREEN).max())
    print(f"    max abs deviation: crate {d_crate:.6f}   corpus {d_corpus:.6f}")
    e1 = d_crate < 5e-4 <= d_corpus
    print(f"    E1 {'HOLDS -- the crate order is correct; ORCH is right' if e1 else 'FALSIFIED -- escalate, do not agree'}")

    print("\n    full corrected camera_to_srgb:")
    for nm, row in zip("RGB", crate):
        print(f"      {nm} row: {row[0]:9.6f} {row[1]:9.6f} {row[2]:9.6f}")

    gr = abs(crate[0][1]) / crate[0][0]
    rg = abs(crate[1][0]) / crate[1][1]
    print("\nE2  LEAK MAGNITUDES")
    print(f"    output red carries camera green: {100*gr:.1f}%   (ORCH 27.4%, corpus said 10.4%)")
    print(f"    output green carries camera red: {100*rg:.1f}%   (ORCH  7.7%, corpus said 20.3%)")
    e2 = abs(100 * gr - 27.4) <= 0.5 and abs(100 * rg - 7.7) <= 0.5
    print(f"    E2 {'HOLDS' if e2 else 'FALSIFIED'}")

    print("\nE3/E4  FORWARD MODEL -- matrix alone, on clean data, no demosaic anywhere")
    off = tifffile.imread(os.path.join(R13, "off.tif")).astype(np.float32)
    on = tifffile.imread(os.path.join(R13, "on.tif")).astype(np.float32)

    def apply_m(img):
        f = img.reshape(-1, 3) @ crate.T.astype(np.float32)
        return f.reshape(img.shape)

    mo, mn = apply_m(off), apply_m(on)
    a_c, n_c, _ = estimate_floored(off[..., 0], off[..., 1], FLOOR)
    b_c, _, _ = estimate_floored(on[..., 0], on[..., 1], FLOOR)
    a_m, n_m, _ = estimate_floored(mo[..., 0], mo[..., 1], FLOOR)
    b_m, _, _ = estimate_floored(mn[..., 0], mn[..., 1], FLOOR)
    t_c, t_m = (b_c - a_c) / EPS, (b_m - a_m) / EPS
    print(f"    clean   n {n_c:5d}  off {a_c*1e6:+8.1f}  on {b_c*1e6:+8.1f}  transfer {t_c:.4f}")
    print(f"    matrix  n {n_m:5d}  off {a_m*1e6:+8.1f}  on {b_m*1e6:+8.1f}  transfer {t_m:.4f}")
    deg = 100.0 * abs(t_m - t_c) / abs(t_c)
    e3 = deg > 5.0
    print(f"    degradation {deg:.1f}%   E3 {'HOLDS -- the matrix alone accounts for a large share' if e3 else 'FALSIFIED -- matrix is minor; demosaic carries it'}")
    e4 = abs(t_m) < abs(t_c)
    print(f"    E4 {'HOLDS -- biased TOWARD zero (attenuation)' if e4 else 'FALSIFIED -- biased AWAY from zero'}")

    print("\n" + "=" * 76)
    print("APPORTIONMENT (the part no internal check could do):")
    print(f"    clean binned-linear transfer            {t_c:.4f}")
    print(f"    + colour matrix only (this script)      {t_m:.4f}")
    print(f"    + matrix + demosaic + gamma (ORCH sRGB)  1.3073")
    print("    The gap between rows 2 and 3 is what the demosaic and tone curve add.")
    print("=" * 76)


if __name__ == "__main__":
    main()
