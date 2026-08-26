"""Acceptance for the z-scored flatness gate, arms from pin-veilz (AFAC2368C4CF).

`coffee-bean` leads. It is the out-of-sample subject: the gate was calibrated
entirely on `flower-bud-alone-cpl`, and ORCH measured the veiling term
independently on `coffee-bean` at -38.2% of far field against flower-bud's
-36.5%, agreeing within 1.7 points on two unrelated captures. It also has a
smooth silhouette with no trichome fringe, so it carries none of the interior
bright ring that confounds the flower-bud edge -- that ring is the election
lane's defect, not this term's, and it is expected to survive here untouched.
"""
from pathlib import Path
import sys
import veil_accept as V

V.OUT = Path(r"C:\dev\strehl-out\VEILZ2")
O = V.OUT
good = True
good &= V.run("coffee-bean  TARGET (out-of-sample, smooth silhouette)",
              {"off": O / "cb-off.tif", "veil-z": O / "cb-on.tif"}, None)
good &= V.run("flower-bud-alone-cpl  TARGET",
              {"off": O / "fb-off.tif", "veil-z": O / "fb-on.tif"}, V.TARGET_BAR)
good &= V.run("109MSDCF  PLACEBO",
              {"off": O / "d109-off.tif", "veil-z": O / "d109-on.tif"}, None)
good &= V.run("pencil-steep-angle-cpl  POLARITY",
              {"off": O / "pen-off.tif", "veil-z": O / "pen-on.tif"}, None)
print("\n" + "=" * 78)
print("ACCEPTANCE:", "PASS" if good else "FAIL")
sys.exit(0 if good else 1)

