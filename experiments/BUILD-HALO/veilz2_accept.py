"""Acceptance for the z-scored flatness gate, arms from pin-veilz (AFAC2368C4CF)."""
from pathlib import Path
import sys
import veil_accept as V

V.OUT = Path(r"C:\dev\strehl-out\VEILZ2")
O = V.OUT
good = True
good &= V.run("flower-bud-alone-cpl  TARGET",
              {"off": O / "fb-off.tif", "veil-z": O / "fb-on.tif"}, V.TARGET_BAR)
good &= V.run("109MSDCF  PLACEBO",
              {"off": O / "d109-off.tif", "veil-z": O / "d109-on.tif"}, None)
good &= V.run("pencil-steep-angle-cpl  POLARITY",
              {"off": O / "pen-off.tif", "veil-z": O / "pen-on.tif"}, None)
print("\n" + "=" * 78)
print("ACCEPTANCE:", "PASS" if good else "FAIL")
sys.exit(0 if good else 1)

