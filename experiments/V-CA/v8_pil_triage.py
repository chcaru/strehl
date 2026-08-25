"""V-CA v8 -- triage ORCH's 27 flagged scripts by HOW PIL is used.

`from PIL import Image` + `Image.open` is not sufficient evidence of exposure.
Three distinct uses have to be separated, and only the first loses data:

  DECODER  np.asarray(Image.open(p)) / .convert() / .getdata()  -> EXPOSED on 16-bit RGB
  TAGS     Image.open(p).tag_v2 ... then raw/memmap byte read   -> NOT exposed
  WRITER   Image.fromarray / ImageDraw / ImageFont / .save      -> NOT exposed

Also proves the classification empirically for ca_radial.py, the one CA-relevant
script on the list, by importing its own loader and checking what it returns.
"""
from __future__ import annotations
import re
from pathlib import Path

EXP = Path(r"C:\dev\blog\death-of-software\projects\strehl\experiments")

DECODE = re.compile(
    r"(np\.(?:as)?array\s*\(\s*Image\.open|Image\.open\([^)]*\)\s*\.convert"
    r"|\.convert\(\s*[\"']RGB|np\.(?:as)?array\s*\(\s*im\b|getdata\(\))")
TAGS = re.compile(r"tag_v2|\.tag\b|TiffTags")
WRITE = re.compile(r"Image\.fromarray|ImageDraw|ImageFont|\.save\(")

rows = []
for f in sorted(EXP.rglob("*.py")):
    try:
        t = f.read_text(encoding="utf-8", errors="replace")
    except OSError:
        continue
    if "PIL" not in t:
        continue
    if not re.search(r"\.tif", t, re.I):
        continue
    cls = ("DECODER  <-- EXPOSED" if DECODE.search(t)
           else "TAGS-only (safe)" if TAGS.search(t)
           else "WRITER-only (safe)" if WRITE.search(t)
           else "unclear -- inspect")
    rows.append((cls, str(f.relative_to(EXP))))

for cls in ("DECODER  <-- EXPOSED", "unclear -- inspect", "TAGS-only (safe)",
            "WRITER-only (safe)"):
    hits = [r for r in rows if r[0] == cls]
    print(f"\n== {cls}  ({len(hits)}) ==")
    for _, p in hits:
        print(f"   {p}")

print("\n\n== EMPIRICAL CHECK: ca_radial.py's own loader ==")
import sys
import numpy as np
sys.path.insert(0, str(EXP / "ORCH-drift-check"))
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "ca_radial", EXP / "ORCH-drift-check" / "ca_radial.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
except SystemExit:
    pass
except Exception as e:                                    # noqa: BLE001
    print(f"   import raised {type(e).__name__}: {e}")

src = Path(r"C:\dev\strehl-out\M110-sheet\bee-3-cpl\default.tif")
try:
    a = m.load_tiff_u16(str(src))
    import tifffile
    b = tifffile.imread(str(src))
    print(f"   ca_radial.load_tiff_u16 -> {a.dtype} {a.shape} max={a.max()}")
    print(f"   tifffile.imread         -> {b.dtype} {b.shape} max={b.max()}")
    print(f"   arrays identical: {np.array_equal(a, b)}")
except Exception as e:                                    # noqa: BLE001
    print(f"   could not run loader: {type(e).__name__}: {e}")
