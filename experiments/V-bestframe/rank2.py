"""Ranked survey with EXPLICIT validity preconditions.

The first version of this table ranked five subjects below flowers-cpl. Every one
of them turned out to have failed a precondition of the instrument, not of the
merge. A collapsed noise floor inflates SNR so every tile counts as detail, and an
uncalibrated merge floor subtracts real signal from the merge arm; both push the
score DOWN. So a low rank and a broken instrument printed identically. They no
longer do: a subject must earn the right to be ranked.
"""
import numpy as np, warnings
from pathlib import Path
from curve import arms
from peaks import peaks_for

warnings.filterwarnings("ignore")
GAL = Path(r"C:\dev\strehl-out\GALLERY-FIXED-SRGB")
RAW = Path(r"D:\personal\macro")
OUT = Path(r"C:\dev\strehl-out\V-BESTFRAME")
GATE = 0.80
FLOOR_LO, FLOOR_HI, FM_TOL, MIN_DETAIL = 5.0, 60.0, 1.5, 20
CALLED_OUT = {"highly-angled-ruler-mm-cpl", "lead-1-cpl", "flowers-cpl", "bee-1-cpl"}

rendered = sorted(p.stem for p in GAL.glob("*.tiff"))
rows, invalid, nosrc = [], [], []
for s in rendered:
    if not (RAW / s).is_dir():
        nosrc.append((s, "no source directory")); continue
    try:
        a = arms(s, peak_min=GATE)
    except Exception as e:
        invalid.append((s, f"arms() raised {type(e).__name__}")); continue
    fl = float(np.sqrt(np.nanmedian(a["F"]))) if np.any(np.isfinite(a["F"])) else np.nan
    ne = int(np.sum(a["snr"] < 0.5))
    real = np.isfinite(a["snr"]) & (a["snr"] >= 3.0)
    nd = int(real.sum())
    if not np.isfinite(fl):
        invalid.append((s, "V1 fixed-pattern floor undefined (no tile reached "
                           "20 px scene displacement)")); continue
    if not (FLOOR_LO <= fl <= FLOOR_HI):
        invalid.append((s, f"V1 floor {fl:.2f} DN outside the {FLOOR_LO:.0f}-"
                           f"{FLOOR_HI:.0f} DN family measured on the other subjects"))
        continue
    fm = float(np.sqrt(a["Fm"]))
    if fm > FM_TOL * fl:
        invalid.append((s, f"V2 merge floor {fm:.1f} DN exceeds single-frame floor "
                           f"{fl:.1f} DN; an average of {a['nd']} frames cannot be "
                           f"noisier than one, so the estimator ate real signal"))
        continue
    if nd < MIN_DETAIL:
        invalid.append((s, f"V3 only {nd} detail tiles < {MIN_DETAIL}")); continue
    r = a["ratio"][real]
    pk = peaks_for(s, a["z"]["anchors"])
    rows.append(dict(s=s, a=a, nd=nd, fl=fl, ne=ne, fm=fm,
                     w=float(np.mean(r >= 1.0) * 100), med=float(np.nanmedian(r)),
                     p05=float(np.nanpercentile(r, 5)), nb=int(np.sum(r < 0.80)),
                     pk=float(np.nanmin(pk)) if np.any(np.isfinite(pk)) else np.nan))

rows.sort(key=lambda d: d["w"])
print(f"V-bestframe survey  |  registration gate peak>={GATE}  |  merge vs best "
      f"single frame, per tile, worst first\n")
h = (f"{'subject':36s} {'frm':>4} {'rd':>3} {'gt':>3} {'floor':>6} {'mfloor':>6} {'detail':>7} "
     f"{'merge>=frm':>10} {'medRatio':>8} {'p05':>6} {'ratio<0.8':>9}")
print(h); print("-" * len(h))
for d in rows:
    mark = " *" if d["s"] in CALLED_OUT else ""
    print(f"{d['s']+mark:36s} {d['a']['nd']:4d} {2*d['a']['na']:3d} {d['a']['ngate']:3d} "
          f"{d['fl']:6.2f} {d['fm']:6.2f} {d['nd']:3d}/352 {d['w']:9.1f}% {d['med']:8.3f} "
          f"{d['p05']:6.3f} {d['nb']:9d}")
print("-" * len(h))
print(f"\nrendered on disk                 {len(rendered):3d}")
print(f"  RANKED above                   {len(rows):3d}")
print(f"  NOT RANKED, instrument invalid {len(invalid):3d}")
for s, why in sorted(invalid):
    print(f"      {s:36s} {why}")
print(f"  no source directory            {len(nosrc):3d}")
for s, why in sorted(nosrc):
    print(f"      {s:36s} {why}")
tot = len(rows) + len(invalid) + len(nosrc)
ok = "OK" if tot == len(rendered) else "MISMATCH -- DO NOT TRUST THIS TABLE"
print(f"  partition sums to              {tot:3d}   {ok}")
print("\n'floor' is that subject's own measured fixed-pattern noise in DN. 'detail' is")
print("tiles of 352 whose best frame holds signal at SNR>=3 above that floor -- a")
print("property of the CAPTURE, not of the merge. 'merge>=frm' is the acceptance")
print("invariant and is meaningful only on those tiles. * = called out by name.")
