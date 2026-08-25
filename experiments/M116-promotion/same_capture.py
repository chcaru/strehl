"""Discipline 832 check: is M93's stack the SAME capture as my M116 bee-3-cpl?

Identical array geometry is not identity of subject. ORCH quoted a 390x ratio
between a render of one subject and a frame of another tonight; the defence is
to establish what is held constant BEFORE comparing. This correlates the
candidate images pixelwise and prints the provenance recorded in each render's
own run ledger.

Read-only. Prints only.
"""
import glob
import json
import os
from pathlib import Path

import numpy as np
import tifffile

M93 = Path(r"C:\dev\strehl-out\M93-out")
M116 = Path(r"C:\dev\strehl-out\M116")


def lum(p, step=4):
    a = tifffile.imread(p)
    if a.dtype != np.uint16:
        raise SystemExit(f"{p} read as {a.dtype}, expected uint16")
    a = a[::step, ::step]
    return (a[..., :3].astype(np.float64).mean(axis=2) if a.ndim == 3
            else a.astype(np.float64))


def corr(a, b):
    a = a.ravel() - a.mean()
    b = b.ravel() - b.mean()
    d = np.sqrt((a * a).sum() * (b * b).sum())
    return float((a * b).sum() / d) if d else float("nan")


CANDS = [
    ("M93 armF-f173  (single frame)", M93 / "armF-f173.tif"),
    ("M93 armF-f143  (single frame)", M93 / "armF-f143.tif"),
    ("M93 armM-gate0-binlin", M93 / "armM-gate0-binlin.tif"),
    ("M93 armM4-gate4-binlin", M93 / "armM4-gate4-binlin.tif"),
    ("M116 bee-3-cpl__A0 (shipped)", M116 / "measure" / "bee-3-cpl__A0.tif"),
    ("M116 bee-3-cpl__M0 (gate 0)", M116 / "measure" / "bee-3-cpl__M0.tif"),
    ("M116 tweezers-cpl__A0", M116 / "measure" / "tweezers-cpl__A0.tif"),
    ("M116 foam__A0", M116 / "measure" / "foam__A0.tif"),
]

print("=== geometry and dtype ===")
imgs = {}
for name, p in CANDS:
    if not p.exists():
        print(f"  {name:<34} MISSING")
        continue
    t = tifffile.TiffFile(p).series[0]
    print(f"  {name:<34} {str(t.shape):<20} {t.dtype}")
    imgs[name] = p

ref = "M93 armF-f173  (single frame)"
print(f"\n=== pixelwise correlation against {ref} (every 4th pixel) ===")
R = lum(imgs[ref])
for name, p in imgs.items():
    a = lum(p)
    if a.shape != R.shape:
        print(f"  {name:<34} GEOMETRY DIFFERS {a.shape} vs {R.shape}")
        continue
    print(f"  {name:<34} r = {corr(R, a):+.4f}")

print("\n=== provenance recorded by each milestone's own ledger ===")
for lg in sorted(glob.glob(str(M116 / "logs" / "*.json"))):
    try:
        d = json.loads(Path(lg).read_text(encoding="utf-8"))
    except Exception:
        continue
    rows = d if isinstance(d, list) else [d]
    for r in rows:
        if isinstance(r, dict) and r.get("subject") == "bee-3-cpl":
            for k in ("capture", "input", "src", "path", "dir", "arm", "cmd"):
                if k in r:
                    print(f"  M116 bee-3-cpl {k}: {str(r[k])[:150]}")
            break
    else:
        continue
    break
