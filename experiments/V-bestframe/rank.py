"""Ranked survey, worst first. Every rendered subject is partitioned into a
counted outcome and the outcomes must sum to the number of renders on disk, so a
subject that was skipped cannot print the same way as a subject that passed.
"""
import numpy as np
from pathlib import Path
from curve import arms

GAL = Path(r"C:\dev\strehl-out\GALLERY-FIXED-SRGB")
RAW = Path(r"D:\personal\macro")
OUT = Path(r"C:\dev\strehl-out\V-BESTFRAME")
GATE = 0.80
CALLED_OUT = {"highly-angled-ruler-mm-cpl", "lead-1-cpl", "flowers-cpl", "bee-1-cpl"}

rendered = sorted(p.stem for p in GAL.glob("*.tiff"))
rows, nosrc, notmeas = [], [], []
for s in rendered:
    if not (RAW / s).is_dir():
        nosrc.append(s); continue
    if not (OUT / f"{s}__paircov_fine.npz").exists() or not list(OUT.glob(f"{s}__fpn_k*.npz")):
        notmeas.append(s); continue
    try:
        a = arms(s, peak_min=GATE)
    except Exception as e:
        notmeas.append(f"{s} [{type(e).__name__}]"); continue
    real = a["snr"] >= 3.0
    n = int(real.sum())
    if n < 5:
        rows.append((s, a, n, np.nan, np.nan, 0)); continue
    r = a["ratio"][real]
    rows.append((s, a, n, float(np.mean(r >= 1.0) * 100), float(np.nanmedian(r)),
                 int(np.sum(r < 0.80))))

rows.sort(key=lambda t: (np.inf if np.isnan(t[3]) else t[3], -t[5]))
print(f"V-bestframe survey  |  peak gate {GATE}  |  merge vs best single frame, per tile\n")
print(f"{'subject':38s} {'frames':>7} {'read':>5} {'detail':>7} {'merge>=frame':>13} "
      f"{'medRatio':>9} {'H2cand':>7}")
print("-" * 92)
for s, a, n, w, med, nb in rows:
    mark = " *" if s in CALLED_OUT else ""
    if np.isnan(w):
        print(f"{s+mark:38s} {a['nd']:7d} {2*a['na']:5d} {n:4d}/352 "
              f"{'TOO FEW DETAIL TILES TO RANK':>13}")
    else:
        print(f"{s+mark:38s} {a['nd']:7d} {2*a['na']:5d} {n:4d}/352 {w:12.1f}% "
              f"{med:9.3f} {nb:7d}")
print("-" * 92)
print(f"rendered on disk            {len(rendered):3d}")
print(f"  measured                  {len(rows):3d}")
print(f"  NOT measured              {len(notmeas):3d}   {', '.join(notmeas) if notmeas else '-'}")
print(f"  no source directory       {len(nosrc):3d}   {', '.join(nosrc) if nosrc else '-'}")
tot = len(rows) + len(notmeas) + len(nosrc)
print(f"  partition sums to         {tot:3d}   "
      f"{'OK' if tot == len(rendered) else 'MISMATCH -- DO NOT TRUST THIS TABLE'}")
print("\n'detail' = tiles of 352 whose best frame holds detail above that subject's own")
print("measured fixed-pattern floor at SNR>=3 (the crossover measured on both headline")
print("subjects). It is a property of the CAPTURE. 'merge>=frame' is the acceptance")
print("invariant and is only meaningful on those tiles. * = called out by name.")
