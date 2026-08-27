"""Commission BUILD-SHARP's OWN 14.97 um resampling term.

That term is sqrt(mean(rise_cr)^2 - mean(rise_nn)^2) between the b-g0-cr and
b-g0-nn arms.  It is only a KERNEL measurement if the two arms elect the SAME
frame at each pixel.  Changing --resampler changes the warp, which changes the
focus field, which can change the election -- the same confound just measured
for the gather flip.  Measured here.

  N1 null      : ALIGN=0, plane vs fullres  -> warp unreachable, election MUST be identical
  N2 null      : ALIGN=0, catmull vs nearest -> warp unreachable, election MUST be identical
  T1 treatment : ALIGN=1, cr-plane vs nn-plane  <- BUILD-SHARP's own 14.97 um comparison
  T2 treatment : ALIGN=1, cr-plane vs cr-fullres <- the gather flip
"""
from __future__ import annotations
import json, os, subprocess, sys, time
from pathlib import Path
import numpy as np
import tifffile

EXE = r"C:\dev\strehl-out\V-GATHER\strehl-pinned.exe"
OUT = Path(r"C:\dev\strehl-out\V-GATHER\esf")
REPO = Path(r"C:\dev\blog\death-of-software\projects\strehl")
NULLS = REPO / "experiments" / "M88b-merge-sharpness" / "out" / "b03_nulls.json"

def imap(subject, tag, align, fullres, resampler):
    p = OUT / f"idx-{subject}--{tag}.tif"
    if p.exists(): return p
    env = dict(os.environ)
    env.update(STREHL_ALIGN=align, STREHL_FULLRES_GATHER=fullres, STREHL_FIX_CA="off",
               STREHL_CACHE_DIR=str(OUT / f"warpcache-{resampler}"))
    env.pop("STREHL_WARPMAP", None)
    cmd = [EXE, "stack", str(Path(r"D:\personal\macro") / subject),
           "--out", str(OUT / f"idx-{subject}--{tag}-img.tif"),
           "--gate", "0", "--resampler", resampler, "--index-map", str(p)]
    t0 = time.perf_counter()
    r = subprocess.run(cmd, env=env, capture_output=True, text=True)
    print(f"  {subject:>14} {tag:<12} rc={r.returncode} {time.perf_counter()-t0:5.1f}s", flush=True)
    if r.returncode != 0:
        print((r.stdout + r.stderr)[-600:]); return None
    return p

ARMS = [("plane",      "1", "0", "catmull-rom"),
        ("fullres",    "1", "1", "catmull-rom"),
        ("nn-plane",   "1", "0", "nearest"),
        ("na-plane",   "0", "0", "catmull-rom"),
        ("na-fullres", "0", "1", "catmull-rom"),
        ("na-nn",      "0", "0", "nearest")]
SUBJ = {"109MSDCF": "109MSDCF", "tweezers": "tweezers-cpl"}

print("rendering index maps ...")
M = {}
for stack, sub in SUBJ.items():
    for tag, al, fr, rs in ARMS:
        p = imap(sub, tag, al, fr, rs)
        if p: M[(stack, tag)] = tifffile.imread(p)

d = json.loads(NULLS.read_text())
rois = d["rois"]
adm = {(x["stack"], x["name"]) for x in d["N1"]["rows"] if x.get("admitted")}

TESTS = [("N1 null   ALIGN=0 plane vs fullres", "na-plane", "na-fullres"),
         ("N2 null   ALIGN=0 catmull vs nearest", "na-plane", "na-nn"),
         ("T1 BUILD-SHARP's own cr vs nn (the 14.97 um term)", "plane", "nn-plane"),
         ("T2 the gather flip, plane vs fullres", "plane", "fullres")]

for label, ta, tb in TESTS:
    print(f"\n=== {label} ===")
    for stack in SUBJ:
        a, b = M.get((stack, ta)), M.get((stack, tb))
        if a is None or b is None:
            print(f"  {stack:>10}: MISSING"); continue
        chg = (a != b)
        line = f"  {stack:>10}: election changed at {100.0*chg.mean():7.3f}% of pixels"
        if chg.any():
            dd = (b.astype(np.int32) - a.astype(np.int32))[chg]
            line += f"   mean idx shift {dd.mean():+7.3f}  max|d| {np.abs(dd).max()}"
        print(line)
        for r in rois:
            if (r["stack"], r["name"]) not in adm or r["stack"] != stack: continue
            y, x, h, w = r["roi"]
            A, B = a[y:y+h, x:x+w], b[y:y+h, x:x+w]
            c = (A != B)
            ma = np.bincount(A.ravel()).argmax(); mb = np.bincount(B.ravel()).argmax()
            print(f"  {'':>10}    {r['name']}: {100.0*c.mean():6.2f}% changed in window, "
                  f"modal frame {ma} -> {mb}")
