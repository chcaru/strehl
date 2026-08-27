"""Measure the gather kernel's blur with the ELECTION HELD FIXED.

The election moves under the flip (34% of pixels), so BUILD-SHARP's --gate 0
paired-reference trick is confounded.  This restricts the ESF to 96x96 windows
where the two arms elected the SAME frame at EVERY pixel, so the only thing
that differs inside the window is the gather.

Admission is PRE-DECLARED and ABSOLUTE, never top-N:
  1. 100.0% election agreement between the arms inside the window
  2. edge axis chosen from the REFERENCE arm only (treatment-blind)
  3. absolute contrast floor CONTRAST_MIN on the reference arm
  4. both ESF fits must succeed
  5. non-overlapping windows (stride 96), every survivor kept

Controls:
  NULL     : na-plane vs na-fullres (byte-identical files) -> every delta must be 0
  POSITIVE : reference vs a planted 0.6 px Gaussian blur of itself -> must read softer
"""
from __future__ import annotations
import json, math, sys, time
from pathlib import Path
import numpy as np
import tifffile
from scipy.ndimage import gaussian_filter

REPO = Path(r"C:\dev\blog\death-of-software\projects\strehl")
sys.path.insert(0, str(REPO / "experiments" / "M88b-merge-sharpness" / "src"))
sys.path.insert(0, str(REPO / "experiments" / "M88-optical-ceiling" / "src"))
import m88blib as M

ESF = Path(r"C:\dev\strehl-out\V-GATHER\esf")
W = 96
CONTRAST_MIN = 2000.0   # DN, absolute, pre-declared

def rd(name):
    for c in (ESF / f"{name}.tif", ESF / f"mem-{name}.tif"):
        if c.exists(): return M.read_merge_plane(c, "G")
    return None

def axis_of(ref, y, x):
    """Edge axis from the REFERENCE arm only. 'horizontal' = edge runs across,
    profile varies with y (m88blib's convention, matched to b03_nulls)."""
    w = ref[y:y+W, x:x+W].astype(np.float64)
    gy = np.abs(np.diff(w.mean(axis=1))).sum()
    gx = np.abs(np.diff(w.mean(axis=0))).sum()
    return ("horizontal", gy) if gy >= gx else ("vertical", gx)

def scan(ref, arm, agree, label, tlimit=900):
    t0 = time.time(); rows = []; nwin = nagree = nfit = 0
    H, Wd = ref.shape
    for y in range(128, H - W - 128, W):
        for x in range(128, Wd - W - 128, W):
            nwin += 1
            if agree is not None and not agree[y:y+W, x:x+W].all():
                continue
            nagree += 1
            ax, _ = axis_of(ref, y, x)
            d = M.paired_delta_registered(ref, arm, (y, x, W, W), ax)
            if d.get("error"): continue
            nfit += 1
            if d["contrast_off"] < CONTRAST_MIN: continue
            rows.append(dict(y=y, x=x, axis=ax, rise_ref=d["rise_off_um"],
                             rise_arm=d["rise_on_um"],
                             delta=d["rise_off_um"] - d["rise_on_um"],
                             contrast=d["contrast_off"],
                             shift=(d.get("shift_dy", 0), d.get("shift_dx", 0))))
            if time.time() - t0 > tlimit: break
        if time.time() - t0 > tlimit: break
    print(f"  {label:<44} windows={nwin:5d} election-clean={nagree:5d} "
          f"fit-ok={nfit:5d} admitted={len(rows):4d}  ({time.time()-t0:.0f}s)")
    return rows

def summarise(label, rows, floor_note=""):
    if not rows:
        print(f"  {label:<44} NO ADMITTED SITES"); return
    d = np.array([r["delta"] for r in rows])
    rr = np.array([r["rise_ref"] for r in rows])
    ra = np.array([r["rise_arm"] for r in rows])
    se = d.std(ddof=1) / math.sqrt(len(d)) if len(d) > 1 else float("nan")
    print(f"  {label:<44} n={len(d):4d}  mean rise_ref={rr.mean():7.3f}  "
          f"mean rise_arm={ra.mean():7.3f}  mean delta={d.mean():+7.3f} "
          f"+/- {1.96*se:.3f} (95% CI)  median={np.median(d):+7.3f}  "
          f"frac arm sharper={100*(d>0).mean():5.1f}% {floor_note}")
    return d

for stack, sub in (("109MSDCF", "109MSDCF"), ("tweezers", "tweezers-cpl")):
    print(f"\n########## {stack} ({sub}) ##########")
    pl, fu = rd(f"{sub}--cr-plane"), rd(f"{sub}--cr-fullres")
    npl, nfu = rd(f"{sub}--nn-plane"), rd(f"{sub}--nn-fullres")
    ipl = tifffile.imread(ESF / f"idx-{sub}--plane.tif")
    ifu = tifffile.imread(ESF / f"idx-{sub}--fullres.tif")
    inn = tifffile.imread(ESF / f"idx-{sub}--nn-plane.tif")
    agree_flip = (ipl == ifu)
    agree_krn  = (ipl == inn)
    print(f"  whole-plane election agreement: flip {100*agree_flip.mean():.2f}% "
          f"| cr-vs-nn {100*agree_krn.mean():.2f}%")

    napl, nafu = rd(f"{sub}--na-plane"), rd(f"{sub}--na-fullres")
    print("\n  --- CONTROLS ---")
    if napl is not None and nafu is not None:
        print(f"  na-plane vs na-fullres byte-identical arrays: "
              f"{np.array_equal(napl, nafu)}")
        summarise("NULL  na-plane vs na-fullres",
                  scan(napl, nafu, None, "NULL  scan", tlimit=300))
    blur = gaussian_filter(pl.astype(np.float32), 0.6).astype(pl.dtype)
    summarise("POSITIVE  plane vs plane+0.6px gaussian",
              scan(pl, blur, None, "POSITIVE scan", tlimit=300))

    print("\n  --- TREATMENT, election held fixed (100% agreement windows) ---")
    summarise("FLIP  cr-plane -> cr-fullres", scan(pl, fu, agree_flip, "FLIP scan"))
    if npl is not None:
        summarise("KERNEL(plane)   cr-plane -> nn-plane",
                  scan(pl, npl, agree_krn, "KERNEL-plane scan"))
    if nfu is not None:
        inf2 = ESF / f"idx-{sub}--nn-fullres.tif"
        if inf2.exists():
            summarise("KERNEL(fullres) cr-fullres -> nn-fullres",
                      scan(fu, nfu, (ifu == tifffile.imread(inf2)), "KERNEL-fullres scan"))
        else:
            print("  KERNEL(fullres): no nn-fullres index map, skipped")
