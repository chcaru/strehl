"""Input provenance audit: were any of M121's INPUTS already narrowed upstream?"""
import pathlib, json, sys
import numpy as np, tifffile
sys.path.insert(0, ".")
from m121_io import sha256

INPUTS = [
    (r"C:\dev\strehl-out\M93-out\armM4-gate4-binlin.tif", "M93", "shipped gate-4 arm (headline)"),
    (r"C:\dev\strehl-out\M93-out\armM-gate0-binlin.tif",  "M93", "gate-0 negative control"),
    (r"C:\dev\strehl-out\M93-out\armF-f143.tif", "M93", "single frame (N1)"),
    (r"C:\dev\strehl-out\M93-out\armF-f158.tif", "M93", "single frame (N1)"),
    (r"C:\dev\strehl-out\M93-out\armF-f173.tif", "M93", "single frame (N1)"),
    (r"C:\dev\strehl-out\M93-out\armF-f193.tif", "M93", "single frame (N1)"),
    (r"C:\dev\strehl-out\M93-out\armF-f208.tif", "M93", "single frame (N1)"),
    (r"C:\dev\strehl-out\M121\e3\armM4-repro.tif", "M121", "my own re-render"),
    (r"C:\dev\strehl-out\M121\e3\index.tif", "M121", "my own index map"),
    (r"C:\dev\strehl-out\M121\tweezers\tweezers-gate4.tif", "M121", "second subject"),
    (r"C:\dev\strehl-out\M121\tweezers\tweezers-1f.tif", "M121", "second subject, 1 frame"),
    (r"C:\dev\strehl-out\M121\tweezers\index.tif", "M121", "second subject index"),
]

print(f"{'file':<34}{'owner':<7}{'dtype':<9}{'bits':>5}{'levels':>9}{'occupied DN':>14}  verdict")
print("-" * 108)
rows = []
for p, owner, what in INPUTS:
    q = pathlib.Path(p)
    if not q.exists():
        print(f"{q.name:<34}{owner:<7}{'MISSING':<9}"); continue
    with tifffile.TiffFile(str(q)) as tf:
        pg = tf.pages[0]
        bits = pg.bitspersample
    a = tifffile.imread(str(q))
    lv = int(np.unique(a).size)
    occ = f"{int(a.min())}..{int(a.max())}"
    narrowed = (a.dtype != np.uint16) or (lv <= 256)
    verdict = "*** NARROWED ***" if narrowed else "clean 16-bit"
    print(f"{q.name:<34}{owner:<7}{str(a.dtype):<9}{bits:>5}{lv:>9}{occ:>14}  {verdict}")
    rows.append({"file": str(q), "owner": owner, "what": what,
                 "dtype": str(a.dtype), "bits": int(bits), "levels": lv,
                 "narrowed": bool(narrowed)})
    del a

print("-" * 108)
# The strongest provenance evidence available: the M93 arm was reproduced from
# the raw frames by M121 itself and is byte-identical.
a = sha256(pathlib.Path(r"C:\dev\strehl-out\M93-out\armM4-gate4-binlin.tif"))
b = sha256(pathlib.Path(r"C:\dev\strehl-out\M121\e3\armM4-repro.tif"))
print(f"M93 shipped arm  sha256 {a[:16]}")
print(f"M121 re-render   sha256 {b[:16]}")
print("BYTE-IDENTICAL -> the input is provably not narrowed upstream"
      if a == b else "*** MISMATCH -- provenance chain is broken ***")
json.dump({"inputs": rows, "byte_identical": a == b},
          open(r"C:\dev\strehl-out\M121\n8\input-provenance.json", "w"), indent=2)
