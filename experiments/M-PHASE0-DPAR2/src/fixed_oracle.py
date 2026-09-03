"""Literal external fixture for DPAR2 C3.

This module deliberately imports neither the plant applicator nor M6.  The
expected values were fixed in PREREGISTRATION.md before the applicator existed.
"""

PAIR_FACTORS = [-0.5, -0.5, -1.0, -1.0, -2.0, -2.0]
DEPTH_STEPS = [-1.0, +1.0, -1.0, +1.0, -1.0, +1.0]
RADII_PX = [1000.0, 2000.0, 1000.0, 2000.0, 1000.0, 2000.0]
AMPLITUDE_PX_PER_STEP_R1000 = 0.300
EXPECTED_RADIAL_PX = [+0.150, -0.300, +0.300, -0.600, +0.600, -1.200]
