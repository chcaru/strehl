"""Run the V-RIM profiler on one linear TIFF. Prints every row it computed
before any verdict, so a wrong conclusion is visible without a re-run."""
import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage

sys.path.insert(0, r"C:\dev\strehl-out\V-RIM")
from vrimlib import (EDGES, load_lum, otsu, place_disc, profile, prominence,
                     segment, signed_distance)

SRC = Path(sys.argv[1])
CH = sys.argv[2] if len(sys.argv) > 2 else "G"
OUTJSON = Path(sys.argv[3]) if len(sys.argv) > 3 else None

shape, lum = load_lum(SRC, CH)
print(f"file      {SRC}")
print(f"shape     {shape}  channel={CH}")

subject, backdrop, diag = segment(lum)
for k, v in diag.items():
    print(f"  seg.{k:26s} {v}")

signed = signed_distance(subject)
print(f"  signed distance range     {signed.min():.1f} .. {signed.max():.1f}")

# --- references, four ways ---------------------------------------------------
valid = backdrop  # profile the BACKDROP only, never subject pixels
m_orch = valid & (signed > 600) & (signed < 1400)
n_orch = int(m_orch.sum())
ref_orch = float(np.median(lum[m_orch])) if n_orch > 500 else float("nan")

dmax = float(signed[valid].max())
m_out = valid & (signed > 0.8 * dmax)
ref_outer = float(np.median(lum[m_out])) if int(m_out.sum()) > 500 else float("nan")

m_300 = valid & (signed > 300)
ref_300 = float(np.median(lum[m_300])) if int(m_300.sum()) > 500 else float("nan")

# modal backdrop: peak of a fine histogram over all backdrop pixels
h, e = np.histogram(lum[valid], bins=1024)
ref_mode = float(0.5 * (e[int(np.argmax(h))] + e[int(np.argmax(h)) + 1]))

# subject interior level, for the contrast normalisation
deep = subject & (signed < -100)
if int(deep.sum()) < 500:
    deep = subject & (signed < -20)
subj_lvl = float(np.median(lum[deep])) if int(deep.sum()) > 100 else float("nan")

print()
print("REFERENCES (linear DN)")
print(f"  ORCH band 600-1400 px      {ref_orch:10.1f}   over {n_orch} px")
print(f"  outer 20% of available d   {ref_outer:10.1f}   (d>{0.8*dmax:.0f})")
print(f"  everything beyond 300 px   {ref_300:10.1f}")
print(f"  modal backdrop             {ref_mode:10.1f}")
print(f"  subject interior median    {subj_lvl:10.1f}   over {int(deep.sum())} px")
print(f"  contrast far-subject       {ref_orch - subj_lvl:10.1f}")

rows = profile(lum, signed, valid)
print()
print("BACKDROP PROFILE, linear DN, outward from the silhouette")
print("   d_lo  d_hi        n        med        q25        q75   vs ref_orch    frac")
for r in rows:
    print(f"  {r['lo']:5d} {r['hi']:5d} {r['n']:9d} {r['med']:10.1f} "
          f"{r['q25']:10.1f} {r['q75']:10.1f} {r['med']-ref_orch:+12.1f} "
          f"{(r['med']-ref_orch)/ref_orch*100:+7.2f}%")

edge = rows[0]["med"] if rows else float("nan")

# --- ring statistic and its own null -----------------------------------------
pr_near = prominence(rows, ref_orch, 0, 200)
pr_all = prominence(rows, ref_orch, 0, 1e9)
null = prominence([r for r in rows if 600 <= r["d"] <= 2000], ref_orch)

print()
print("RING STATISTIC (interior local max, height above the trough beyond it)")
print(f"  near window d<=200 px : {pr_near}")
print(f"  whole profile         : {pr_all}")
print(f"  NULL, same statistic on the subject-free stretch 600-2000 px:")
print(f"                          {null}")

# --- placebo -----------------------------------------------------------------
placebo = None
try:
    disc, dinfo = place_disc(subject, backdrop, signed)
    if dinfo["room"] > 400:
        sd = signed_distance(disc)
        pvalid = backdrop & ~subject & (signed > 0)
        prows = profile(lum, sd, pvalid, minpix=100)
        pref_m = pvalid & (sd > 0.6 * float(sd[pvalid].max()))
        pref = float(np.median(lum[pref_m])) if int(pref_m.sum()) > 200 else float("nan")
        print()
        print(f"PLACEBO disc r={dinfo['radius']:.0f} at ({dinfo['cx']},{dinfo['cy']}), "
              f"room={dinfo['room']:.0f} px, ref={pref:.1f}")
        print("   d_lo  d_hi        n        med   vs ref    frac")
        for r in prows:
            print(f"  {r['lo']:5d} {r['hi']:5d} {r['n']:9d} {r['med']:10.1f} "
                  f"{r['med']-pref:+9.1f} {(r['med']-pref)/pref*100:+7.2f}%")
        pedge = prows[0]["med"] if prows else float("nan")
        pprom = prominence(prows, pref, 0, 200)
        placebo = dict(radius=dinfo["radius"], ref=pref, edge=pedge,
                       edge_frac=(pedge - pref) / pref if pref == pref else None,
                       prom=pprom)
        print(f"  placebo darkening at 0-1 px: {(pedge-pref)/pref*100:+.2f}% "
              f"(subject's is {(edge-ref_orch)/ref_orch*100:+.2f}%)")
        print(f"  placebo ring prominence    : {pprom}")
    else:
        print()
        print(f"PLACEBO skipped: only {dinfo['room']:.0f} px of clear backdrop")
except Exception as ex:  # pragma: no cover
    print(f"PLACEBO failed: {ex}")

# --- zero-point sensitivity ---------------------------------------------------
print()
print("ZERO-POINT SENSITIVITY (mask grown/shrunk, profile recomputed)")
print("   shift   subj%     edge DN    edge frac    ring d   ring frac")
zp = {}
for shift in (-10, -5, -2, 0, 2, 5, 10):
    if shift == 0:
        s2, sub2 = signed, subject
    elif shift > 0:
        sub2 = ndimage.binary_dilation(subject, iterations=shift)
        s2 = signed_distance(sub2)
    else:
        sub2 = ndimage.binary_erosion(subject, iterations=-shift)
        s2 = signed_distance(sub2)
    v2 = backdrop & (s2 > 0) if shift <= 0 else (backdrop & ~sub2)
    r2 = profile(lum, s2, v2)
    if not r2:
        continue
    e2 = r2[0]["med"]
    p2 = prominence(r2, ref_orch, 0, 200)
    zp[shift] = dict(edge=e2, frac=(e2 - ref_orch) / ref_orch,
                     ring=p2)
    rd = f"{p2['d']:8.1f}" if p2 else "     ---"
    rf = f"{p2['prom_frac']*100:+9.2f}%" if p2 else "       ---"
    print(f"  {shift:+6d} {sub2.mean()*100:7.2f} {e2:11.1f} "
          f"{(e2-ref_orch)/ref_orch*100:+11.2f}% {rd} {rf}")

# --- verdict, printed last ----------------------------------------------------
print()
print("SUMMARY")
print(f"  darkening at 0-1 px : {edge-ref_orch:+.1f} DN = "
      f"{(edge-ref_orch)/ref_orch*100:+.2f}% of far field")
if subj_lvl == subj_lvl:
    print(f"                        = {(edge-ref_orch)/(ref_orch-subj_lvl)*100:+.2f}% "
          f"of far-minus-subject contrast")
    print(f"  optical density     : {np.log10(ref_orch/max(edge,1e-6)):+.4f} dex")
if pr_near:
    print(f"  ring (d<=200)       : d={pr_near['d']:.1f} px, "
          f"{pr_near['prom']:+.1f} DN = {pr_near['prom_frac']*100:+.2f}%")
else:
    print("  ring (d<=200)       : none found")
if null:
    print(f"  null prominence     : {null['prom_frac']*100:+.2f}%  "
          f"(the floor the ring must beat)")

if OUTJSON:
    out = dict(
        file=str(SRC), channel=CH, shape=list(shape), seg=diag,
        ref_orch=ref_orch, ref_outer=ref_outer, ref_300=ref_300,
        ref_mode=ref_mode, subj_lvl=subj_lvl, edge=edge,
        n_orch_ref_px=n_orch, dmax=dmax,
        rows=rows, prom_near=pr_near, prom_all=pr_all, null=null,
        placebo=placebo,
        zero_point={str(k): dict(edge=v["edge"], frac=v["frac"],
                                 ring=v["ring"]) for k, v in zp.items()},
    )
    OUTJSON.parent.mkdir(parents=True, exist_ok=True)
    OUTJSON.write_text(json.dumps(out, indent=1))
    print(f"\nwrote {OUTJSON}")
