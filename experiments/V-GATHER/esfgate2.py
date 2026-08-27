"""Sensitivity of the flip's measured ESF delta to ELECTION CONTAMINATION.

No 96x96 window has 100% election agreement, so instead: fit every admitted
window ONCE, then aggregate over nested subsets ranked by how election-clean
they are.  If the delta is flat in the agreement fraction, contamination is not
driving it.  If it swings, it is -- and the number means nothing.

Statistics reported are the MEDIAN and the SIGN FRACTION, because the positive
control showed the mean is heavy-tailed.
"""
from __future__ import annotations
import math, sys, time
from pathlib import Path
import numpy as np
import tifffile
from scipy.ndimage import gaussian_filter

REPO = Path(r"C:\dev\blog\death-of-software\projects\strehl")
sys.path.insert(0, str(REPO / "experiments" / "M88b-merge-sharpness" / "src"))
sys.path.insert(0, str(REPO / "experiments" / "M88-optical-ceiling" / "src"))
import m88blib as M

ESF = Path(r"C:\dev\strehl-out\V-GATHER\esf")
W, CONTRAST_MIN = 96, 2000.0

def rd(n):
    for c in (ESF / f"{n}.tif", ESF / f"mem-{n}.tif"):
        if c.exists(): return M.read_merge_plane(c, "G")
    return None

def axis_of(ref, y, x):
    w = ref[y:y+W, x:x+W].astype(np.float64)
    gy = np.abs(np.diff(w.mean(axis=1))).sum(); gx = np.abs(np.diff(w.mean(axis=0))).sum()
    return "horizontal" if gy >= gx else "vertical"

def binom_p(k, n):
    """two-sided sign test vs p=0.5, normal approx"""
    if n == 0: return float("nan")
    z = (k - n / 2) / math.sqrt(n / 4)
    return math.erfc(abs(z) / math.sqrt(2))

def scan(ref, arm, agree):
    rows = []
    H, Wd = ref.shape
    for y in range(128, H - W - 128, W):
        for x in range(128, Wd - W - 128, W):
            ax = axis_of(ref, y, x)
            d = M.paired_delta_registered(ref, arm, (y, x, W, W), ax)
            if d.get("error") or d["contrast_off"] < CONTRAST_MIN: continue
            rows.append((d["rise_off_um"] - d["rise_on_um"], d["rise_off_um"],
                         d["rise_on_um"],
                         float(agree[y:y+W, x:x+W].mean()) if agree is not None else 1.0))
    return rows

def report(label, rows, thresholds=(1.0, 0.95, 0.90, 0.80, 0.70, 0.0)):
    if not rows: print(f"  {label}: no sites"); return
    a = np.array([r[3] for r in rows]); d = np.array([r[0] for r in rows])
    rr = np.array([r[1] for r in rows]); ra = np.array([r[2] for r in rows])
    print(f"  {label}")
    print(f"    election agreement per window: max={a.max():.4f} p95={np.percentile(a,95):.4f} "
          f"median={np.median(a):.4f} min={a.min():.4f}")
    print(f"    {'agree>=':>8} {'n':>4} {'med rise_ref':>13} {'med rise_arm':>13} "
          f"{'med delta':>10} {'%arm sharper':>13} {'sign p':>9}")
    for t in thresholds:
        m = a >= t
        if m.sum() < 3: 
            print(f"    {t:8.2f} {m.sum():4d}   (too few)"); continue
        k = int((d[m] > 0).sum())
        print(f"    {t:8.2f} {m.sum():4d} {np.median(rr[m]):13.3f} {np.median(ra[m]):13.3f} "
              f"{np.median(d[m]):10.3f} {100.0*k/m.sum():13.1f} {binom_p(k, int(m.sum())):9.2e}")

for stack, sub in (("109MSDCF", "109MSDCF"), ("tweezers", "tweezers-cpl")):
    print(f"\n########## {stack} ({sub}) ##########")
    pl, fu = rd(f"{sub}--cr-plane"), rd(f"{sub}--cr-fullres")
    npl = rd(f"{sub}--nn-plane")
    ipl = tifffile.imread(ESF / f"idx-{sub}--plane.tif")
    ifu = tifffile.imread(ESF / f"idx-{sub}--fullres.tif")
    inn = tifffile.imread(ESF / f"idx-{sub}--nn-plane.tif")

    napl, nafu = rd(f"{sub}--na-plane"), rd(f"{sub}--na-fullres")
    report("NULL      na-plane -> na-fullres (byte-identical)", scan(napl, nafu, None), (1.0,))
    report("POSITIVE  cr-plane -> +0.6px gaussian (must read NEGATIVE)",
           scan(pl, gaussian_filter(pl.astype(np.float32), 0.6).astype(pl.dtype), None), (1.0,))
    report("POSITIVE  cr-plane -> +1.2px gaussian (must read NEGATIVE, bigger)",
           scan(pl, gaussian_filter(pl.astype(np.float32), 1.2).astype(pl.dtype), None), (1.0,))
    report("FLIP      cr-plane -> cr-fullres  (+ = fullres SHARPER)", scan(pl, fu, (ipl == ifu)))
    report("KERNEL    cr-plane -> nn-plane    (+ = nn SHARPER; BUILD-SHARP's 14.97 term)",
           scan(pl, npl, (ipl == inn)))
