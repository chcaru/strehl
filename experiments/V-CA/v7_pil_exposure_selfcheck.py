"""V-CA v7 -- ORCH's PIL 16-bit RGB hazard, applied to my own audit.

Rule: re-run rather than reason.  Grepping for `from PIL` proves what the source
says; this proves what the reader actually returns on the exact files every V-CA
number was computed from.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import tifffile

ROOT = Path(r"C:\dev\strehl-out\M110-sheet")
FILES = [
    ("bee-3-cpl", "default.tif"), ("bee-3-cpl", "ca.tif"),
    ("bee-3-cpl", "lind-default.tif"), ("bee-3-cpl", "lind-ca.tif"),
    ("flat-on-ruler-cpl", "default.tif"), ("flat-on-ruler-cpl", "ca.tif"),
]

print(f"{'file':<38}{'tifffile dtype':>16}{'max':>8}{'levels':>9}"
      f"{'| PIL mode':>12}{'PIL dtype':>12}{'PIL levels':>12}")
for sub, name in FILES:
    p = ROOT / sub / name
    a = tifffile.imread(str(p))
    try:
        from PIL import Image
        im = Image.open(str(p))
        b = np.asarray(im)
        pil = (im.mode, str(b.dtype), len(np.unique(b[::13, ::13])))
    except Exception as e:                       # noqa: BLE001
        pil = ("ERROR", type(e).__name__, -1)
    print(f"{sub + '/' + name:<38}{str(a.dtype):>16}{int(a.max()):>8}"
          f"{len(np.unique(a[::13, ::13])):>9}{pil[0]:>12}{pil[1]:>12}{pil[2]:>12}")

print("\nThe magnitudes V-CA reported, in 16-bit counts, against the 8-bit floor:")
print("  PIL quantisation step on a 0..65535 range = 257 counts")
for label, val in [
    ("mean |dG| (bee, sRGB)", 50.03),
    ("mean |dB| (bee, sRGB)", 54.17),
    ("band-0 chroma change (bee, sRGB)", 3127.01 - 2208.92),
    ("band-0 chroma change (bee, LINEAR)", 819.22 - 582.26),
    ("whole-frame chroma change (bee, LINEAR)", 494.21 - 476.51),
]:
    print(f"  {label:<42}{val:9.2f} counts   = {val/257:6.2f} PIL steps"
          f"   {'BELOW FLOOR' if val < 257 else 'above floor'}")
