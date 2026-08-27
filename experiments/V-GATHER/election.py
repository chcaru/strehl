"""Does the gather flip change WHICH FRAME is elected?

BUILD-SHARP §1(a) rests on "--gate 0 => output is byte-identical to the elected
frame", and the user proposed using that as an exact paired reference across
the flip.  That argument is only valid if the ELECTION is the same in both
arms.  The election is computed from the focus field, which is computed from
the WARPED frames -- so the flip can move it.  Measured here, not assumed.

--index-map writes on the PLANE grid (half sensor res), which is exactly the
grid b03_nulls.json's ROI windows are stated in.  No resampling, no gauge.
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
SUBJ = {"109MSDCF": "109MSDCF", "tweezers": "tweezers-cpl"}

def render(subject, fullres):
    tag = "fullres" if fullres == "1" else "plane"
    imap = OUT / f"idx-{subject}--{tag}.tif"
    tif = OUT / f"idx-{subject}--{tag}-img.tif"
    if imap.exists():
        return imap
    env = dict(os.environ)
    env.update(STREHL_ALIGN="1", STREHL_FULLRES_GATHER=fullres, STREHL_FIX_CA="off",
               STREHL_CACHE_DIR=str(OUT / "warpcache-catmull-rom"))
    env.pop("STREHL_WARPMAP", None)
    cmd = [EXE, "stack", str(Path(r"D:\personal\macro") / subject), "--out", str(tif),
           "--gate", "0", "--resampler", "catmull-rom", "--index-map", str(imap)]
    t0 = time.perf_counter()
    r = subprocess.run(cmd, env=env, capture_output=True, text=True)
    print(f"  {subject} {tag}: rc={r.returncode} {time.perf_counter()-t0:.1f}s")
    if r.returncode != 0:
        print((r.stdout + r.stderr)[-800:]); return None
    return imap

rois = json.loads(NULLS.read_text())["rois"]
adm = {(x["stack"], x["name"]) for x in json.loads(NULLS.read_text())["N1"]["rows"]
       if x.get("admitted")}

print("rendering index maps ...")
maps = {}
for stack, sub in SUBJ.items():
    for fr, tag in (("0", "plane"), ("1", "fullres")):
        p = render(sub, fr)
        if p: maps[(stack, tag)] = tifffile.imread(p)

print("\n=== election map, whole plane ===")
for stack in SUBJ:
    a, b = maps.get((stack, "plane")), maps.get((stack, "fullres"))
    if a is None or b is None: continue
    diff = (a != b)
    print(f"  {stack:>10}: shape={a.shape} dtype={a.dtype}  frames_used_plane="
          f"{len(np.unique(a))} fullres={len(np.unique(b))}")
    print(f"  {'':>10}  pixels whose ELECTED FRAME changed: {diff.sum()} / {diff.size} "
          f"= {100.0*diff.sum()/diff.size:.3f}%")
    d = (b.astype(np.int32) - a.astype(np.int32))
    print(f"  {'':>10}  index shift where changed: mean={d[diff].mean():+.3f} "
          f"median={np.median(d[diff]):+.1f} p5={np.percentile(d[diff],5):+.1f} "
          f"p95={np.percentile(d[diff],95):+.1f} max|d|={np.abs(d).max()}")

print("\n=== election INSIDE each admitted ESF window (the ROIs the budget uses) ===")
print(f"{'ROI':>5} {'stack':>10} {'window':>22} {'chg %':>8} {'plane mode':>11} "
      f"{'fullres mode':>13} {'mean idx shift':>15}")
for r in rois:
    key = (r["stack"], r["name"])
    if key not in adm or r["stack"] not in SUBJ: continue
    y, x, h, w = r["roi"]
    a, b = maps.get((r["stack"], "plane")), maps.get((r["stack"], "fullres"))
    if a is None or b is None: continue
    A, B = a[y:y+h, x:x+w], b[y:y+h, x:x+w]
    chg = (A != B)
    ma = np.bincount(A.ravel()).argmax(); mb = np.bincount(B.ravel()).argmax()
    print(f"{r['name']:>5} {r['stack']:>10} {str((y,x,h,w)):>22} "
          f"{100.0*chg.mean():8.2f} {ma:11d} {mb:13d} "
          f"{(B.astype(int)-A.astype(int)).mean():+15.3f}")
