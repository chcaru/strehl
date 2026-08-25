"""PRE-REGISTRATION + prediction for the sRGB-matrix explanation of the
section 14 green/blue coupling.

Registered BEFORE the linear renders are measured.

Hypothesis (ORCH, from M113): output green carries camera red through the
non-diagonal camera_to_srgb matrix, so ANY change to camera red produces a
proportional change in output green with no optics, election, demosaic or
resampler involved. A CONSTANT |dG|/|dR| across radius is that signature.

Section 14 measured |dG|/|dR| = 0.087..0.110, constant across radius, on
--srgb renders. merge_cmd.rs:77 states --srgb applies "the sRGB transfer curve
AND the camera's colour matrix. For looking at, NOT for measuring." So the
measurement was taken through the matrix.

In camera space CA displaces RED only: eps_r is fitted, eps_b is None (blue
never fitted), and green is the reference channel with zero displacement by
construction. So if the matrix is the whole mechanism:

    dG_out = M[1][0] * dR_cam      dR_out = M[0][0] * dR_cam
    ratio  = |M[1][0]| / |M[0][0]|,  independent of radius.

REGISTERED BARS (pass/fail stated before looking at the linear renders):

  P1  The predicted ratio |M[1][0]|/|M[0][0]| lands inside or near the
      measured sRGB band 0.087..0.110. Generous: within [0.04, 0.25].
      If it misses badly the matrix cannot be the sole mechanism.

  P2  In LINEAR camera-native output the ratio COLLAPSES: median
      |dG|/|dR| < 0.02 over pixels where |dR| is above threshold.
      Collapse => matrix explains section 14, three candidates die at once.

  P3  If instead the linear ratio SURVIVES at >= 0.05, the matrix is
      exonerated and a real mechanism (election / demosaic / resample)
      remains. That is the more interesting outcome and must not be
      suppressed.

  P4  Sanity: the linear renders must differ from each other (CA is live)
      and must differ from the --srgb renders (different pipeline).
"""

import numpy as np

SRGB_TO_XYZ_D65 = np.array([
    [0.4124564, 0.3575761, 0.1804375],
    [0.2126729, 0.7151522, 0.0721750],
    [0.0193339, 0.1191920, 0.9503041],
], dtype=np.float64)

# color.rs:812, the reference body constant used by this module's tests.
# ASSUMPTION: the decoder supplies the same characterisation for bee-3-cpl.
# Flagged, not verified -- the render reads xyz_to_cam from the raw file.
A7C2_XYZ_TO_CAM = np.array([
    [0.7460, -0.2365, -0.0588],
    [-0.5687, 1.3442, 0.2474],
    [-0.0624, 0.1156, 0.6584],
], dtype=np.float64)


def camera_to_srgb(xyz_to_cam):
    """Replicates color.rs::camera_to_srgb: compose, row-normalise, invert."""
    cam_from_srgb = xyz_to_cam @ SRGB_TO_XYZ_D65
    sums = cam_from_srgb.sum(axis=1, keepdims=True)
    assert np.all(np.abs(sums) > 1e-9), "singular row sum"
    cam_from_srgb = cam_from_srgb / sums
    return np.linalg.inv(cam_from_srgb)


def main():
    m = camera_to_srgb(A7C2_XYZ_TO_CAM)
    np.set_printoptions(precision=4, suppress=True)
    print(__doc__)
    print("=" * 68)
    print("camera_to_srgb (reference body):")
    for i, nm in enumerate("RGB"):
        print(f"  {nm}_out = {m[i,0]:+.4f} R  {m[i,1]:+.4f} G  {m[i,2]:+.4f} B"
              f"   (row sum {m[i].sum():.6f})")
    print()
    print("Row sums must be 1.0 by construction (neutral-preserving).")

    ratio = abs(m[1, 0]) / abs(m[0, 0])
    ratio_b = abs(m[2, 0]) / abs(m[0, 0])
    print()
    print(f"PREDICTED |dG_out|/|dR_out| = |{m[1,0]:.4f}|/|{m[0,0]:.4f}| = {ratio:.4f}")
    print(f"PREDICTED |dB_out|/|dR_out| = |{m[2,0]:.4f}|/|{m[0,0]:.4f}| = {ratio_b:.4f}")
    print()
    print(f"Section 14 MEASURED band (sRGB): 0.087 .. 0.110")
    lo, hi = 0.087, 0.110
    inband = lo <= ratio <= hi
    near = 0.04 <= ratio <= 0.25
    print(f"  P1 inside measured band exactly : {inband}")
    print(f"  P1 within generous [0.04,0.25]  : {near}  <-- the registered bar")
    print()
    print("ORCH relayed the green row as [-0.4530, +2.2300, -0.7770].")
    print(f"  computed green row            : [{m[1,0]:+.4f}, {m[1,1]:+.4f}, {m[1,2]:+.4f}]")
    print("  color.rs:224 doc comment      : [-0.115, +1.489, -0.374]")
    print("  -> if these three disagree, the relayed numbers are for a")
    print("     different body/characterisation and the RATIO is what matters,")
    print("     not the absolute coefficients.")


if __name__ == "__main__":
    main()
