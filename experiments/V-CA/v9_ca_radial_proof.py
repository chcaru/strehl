"""V-CA v9 -- prove or disprove exposure of ca_radial.py, the one CA-relevant
script on ORCH's list, by running ITS loader against tifffile on a real file."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import numpy as np
import tifffile

EXP = Path(r"C:\dev\blog\death-of-software\projects\strehl\experiments")
SRC = Path(r"C:\dev\strehl-out\M110-sheet\bee-3-cpl\default.tif")

spec = importlib.util.spec_from_file_location(
    "ca_radial", EXP / "ORCH-drift-check" / "ca_radial.py")
m = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(m)
except SystemExit:
    pass

got = m.load_tiff_u16(str(SRC))
if isinstance(got, tuple):
    print(f"   loader returns a {len(got)}-tuple: "
          + ", ".join(type(x).__name__ for x in got))
    arr = next(x for x in got if isinstance(x, np.ndarray))
else:
    arr = got

ref = tifffile.imread(str(SRC))
print(f"\n   ca_radial.load_tiff_u16 -> dtype={arr.dtype} shape={arr.shape} "
      f"min={arr.min()} max={arr.max()}")
print(f"   tifffile.imread         -> dtype={ref.dtype} shape={ref.shape} "
      f"min={ref.min()} max={ref.max()}")
same = arr.shape == ref.shape and np.array_equal(arr, ref)
print(f"\n   BYTE-IDENTICAL TO tifffile: {same}")
print(f"   distinct levels  loader {len(np.unique(arr[::13, ::13]))}"
      f"   tifffile {len(np.unique(ref[::13, ::13]))}")
print(f"\n   VERDICT: ca_radial.py is {'NOT EXPOSED' if same else 'EXPOSED'} "
      "-- PIL is used as a TAG READER, the pixels are read raw.")
