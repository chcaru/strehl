"""One table, every rendered subject, nothing silently dropped.

Two estimates of the merge arm are shown side by side because the strict one is
unavailable on most subjects at this sampling depth:

  strict : merge floor Fm as estimated from empty tiles / a low percentile.
  capped : Fm replaced by min(Fm, F) per tile. The merge is an average of N
           frames, so its noise floor cannot exceed a single frame's
           fixed-pattern floor F. Capping therefore removes a physically
           impossible over-subtraction -- but it makes the merge arm as strong as
           physics allows, so the capped column is an UPPER BOUND on merge
           performance, not a best estimate. A subject that still looks bad in
           the capped column is bad.
"""
import numpy as np, warnings
from pathlib import Path
from curve import arms
from peaks import peaks_for

warnings.filterwarnings("ignore")
GAL = Path(r"C:\dev\strehl-out\GALLERY-FIXED-SRGB")
RAW = Path(r"D:\personal\macro")
GATE, FLOOR_LO, FLOOR_HI, FM_TOL = 0.80, 5.0, 60.0, 1.5
CALLED_OUT = {"highly-angled-ruler-mm-cpl", "lead-1-cpl", "flowers-cpl", "bee-1-cpl"}

rendered = sorted(p.stem for p in GAL.glob("*.tiff"))
rows, unmeasurable = [], []
for s in rendered:
    if not (RAW / s).is_dir():
        unmeasurable.append((s, "no source directory")); continue
    try:
        a = arms(s, peak_min=GATE)
    except Exception as e:
        unmeasurable.append((s, f"arms() raised {type(e).__name__}")); continue
    fl = float(np.sqrt(np.nanmedian(a["F"]))) if np.any(np.isfinite(a["F"])) else np.nan
    if not np.isfinite(fl):
        unmeasurable.append((s, "fixed-pattern floor undefined: no tile reached 20 px "
                                "scene displacement (merge is unregistered)")); continue
    if not (FLOOR_LO <= fl <= FLOOR_HI):
        unmeasurable.append((s, f"floor {fl:.2f} DN is outside the {FLOOR_LO:.0f}-"
                                f"{FLOOR_HI:.0f} DN family measured on every other "
                                f"subject")); continue
    real = np.isfinite(a["snr"]) & (a["snr"] >= 3.0)
    nd = int(real.sum())
    fm = float(np.sqrt(a["Fm"]))
    Smt_c = np.maximum(a["Em"] - np.minimum(a["Fm"], a["F"]), 0.0)
    with np.errstate(divide="ignore", invalid="ignore"):
        rc = np.sqrt(Smt_c) / np.sqrt(np.maximum(a["Sft"], 1e-12))
    r, rcap = a["ratio"][real], rc[real]
    pk = peaks_for(s, a["z"]["anchors"])
    rows.append(dict(s=s, nd=nd, fl=fl, fm=fm, frm=a["nd"], rd=2 * a["na"],
                     gt=a["ngate"], strict=fm <= FM_TOL * fl,
                     w=float(np.mean(r >= 1.0) * 100), med=float(np.nanmedian(r)),
                     wc=float(np.mean(rcap >= 1.0) * 100),
                     medc=float(np.nanmedian(rcap)),
                     p05c=float(np.nanpercentile(rcap, 5)),
                     nbc=int(np.sum(rcap < 0.80)),
                     pk=float(np.nanmin(pk)) if np.any(np.isfinite(pk)) else np.nan))

rows.sort(key=lambda d: d["wc"])
print(f"V-bestframe survey  |  registration gate peak>={GATE}  |  merge vs best "
      f"single frame, per tile, worst first\n")
h = (f"{'subject':36s} {'frm':>4} {'rd':>3} {'gt':>3} {'pkMin':>6} {'floor':>6} "
     f"{'mfloor':>6} {'detail':>7} {'CAPPED>=frm':>11} {'medR':>6} {'p05':>6} "
     f"{'<0.8':>5} {'strict>=frm':>11} {'V2':>3}")
print(h); print("-" * len(h))
for d in rows:
    mark = " *" if d["s"] in CALLED_OUT else ""
    st = f"{d['w']:10.1f}%" if d["strict"] else f"{'--':>11}"
    print(f"{d['s']+mark:36s} {d['frm']:4d} {d['rd']:3d} {d['gt']:3d} {d['pk']:6.3f} "
          f"{d['fl']:6.2f} {d['fm']:6.2f} {d['nd']:3d}/352 {d['wc']:10.1f}% "
          f"{d['medc']:6.2f} {d['p05c']:6.3f} {d['nbc']:5d} {st} "
          f"{'ok' if d['strict'] else 'NO':>3}")
print("-" * len(h))
print(f"\nrendered on disk        {len(rendered):3d}")
print(f"  measured and ranked   {len(rows):3d}   "
      f"({sum(1 for d in rows if d['strict'])} of them with a valid strict merge floor)")
print(f"  NOT MEASURABLE        {len(unmeasurable):3d}")
for s, why in sorted(unmeasurable):
    print(f"      {s:36s} {why}")
tot = len(rows) + len(unmeasurable)
print(f"  partition sums to     {tot:3d}   "
      f"{'OK' if tot == len(rendered) else 'MISMATCH -- DO NOT TRUST THIS TABLE'}")
print("\n'detail' counts tiles of 352 where the best FRAME holds signal at SNR>=3 above")
print("that subject's own fixed-pattern floor. It is computed from the frame arm and")
print("the floor alone -- the merge never enters it -- so it is a property of the")
print("CAPTURE and is immune to the merge-floor problem that invalidates column")
print("'strict' on most subjects. * = called out by name.")
