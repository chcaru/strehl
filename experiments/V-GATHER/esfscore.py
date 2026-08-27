"""Does BUILD-SHARP §1's 14.97 um resampling term survive the gather flip?

BUILD-SHARP's recipe, re-derived by V-GATHER from its own stored JSONs:
    a = sqrt( mean(rise_cr)^2 - mean(rise_nn)^2 )
pooled over the ADMITTED ROIs, on the --gate 0 arms, reference b-g0-cr.
That yielded sqrt(49.2296^2 - 46.8968^2) = 14.977 um.

Here the SAME recipe is run twice from ONE binary:
    plane   family: cr-plane   vs nn-plane    (STREHL_FULLRES_GATHER=0)  <- must reproduce ~14.97
    fullres family: cr-fullres vs nn-fullres  (STREHL_FULLRES_GATHER=1)  <- the answer

m88blib is IMPORTED UNMODIFIED, exactly as esf.py requires.
"""
from __future__ import annotations
import json, math, sys
from pathlib import Path
import numpy as np

REPO = Path(r"C:\dev\blog\death-of-software\projects\strehl")
sys.path.insert(0, str(REPO / "experiments" / "M88b-merge-sharpness" / "src"))
sys.path.insert(0, str(REPO / "experiments" / "M88-optical-ceiling" / "src"))
import m88blib as M

ESF = Path(r"C:\dev\strehl-out\V-GATHER\esf")
NULLS = REPO / "experiments" / "M88b-merge-sharpness" / "out" / "b03_nulls.json"
STACK_DIR = {"109MSDCF": "109MSDCF", "ruler": "highly-angled-ruler-mm-cpl",
             "tweezers": "tweezers-cpl"}

def load_rois():
    d = json.loads(NULLS.read_text())
    adm = {(r["stack"], r["name"]): r for r in d["N1"]["rows"]}
    out = []
    for r in d["rois"]:
        a = adm.get((r["stack"], r["name"]), {})
        out.append(dict(stack=r["stack"], name=r["name"], roi=tuple(r["roi"]),
                        axis=r["axis"], admitted=bool(a.get("admitted", False)),
                        floor_um=float(a.get("p95_abs_um", float("nan")))))
    return out

_cache = {}
def plane(subject, arm):
    key = (subject, arm)
    if key in _cache: return _cache[key]
    for cand in (ESF / f"{subject}--{arm}.tif", ESF / f"mem-{subject}--{arm}.tif"):
        if cand.exists():
            _cache[key] = (M.read_merge_plane(cand, "G"), cand.name)
            return _cache[key]
    _cache[key] = (None, None)
    return _cache[key]

print("instrument constants:", {k: getattr(M, k) for k in
      ("MERGE_PITCH_UM", "BIN_UM", "TAPER", "CORE_UM", "HALF_WIDTH_UM") if hasattr(M, k)})
print()

rois = load_rois()
FAMILIES = [("plane", "cr-plane", "nn-plane"), ("fullres", "cr-fullres", "nn-fullres")]
rows = []

for stack in ("109MSDCF", "tweezers", "ruler"):
    sub = STACK_DIR[stack]
    sel = [r for r in rois if r["stack"] == stack and r["admitted"]]
    if not sel: continue
    print(f"=== {stack} ({sub}) -- ADMITTED ROIs only ===")
    print(f"{'ROI':>5} {'floor':>7} {'family':>8} {'rise_cr':>9} {'rise_nn':>9} "
          f"{'delta':>8} {'a_perROI':>9} {'shift':>8} {'c_cr':>8} {'c_nn':>8}")
    for r in sel:
        for fam, acr, ann in FAMILIES:
            pcr, ncr = plane(sub, acr); pnn, nnn = plane(sub, ann)
            if pcr is None or pnn is None:
                print(f"{r['name']:>5} {r['floor_um']:7.4f} {fam:>8}   MISSING ARM "
                      f"({acr if pcr is None else ann})"); continue
            d = M.paired_delta_registered(pcr, pnn, r["roi"], r["axis"])
            if d.get("error"):
                print(f"{r['name']:>5} {r['floor_um']:7.4f} {fam:>8}   ERROR {d['error'][:60]}")
                rows.append(dict(stack=stack, roi=r["name"], family=fam, error=d["error"]))
                continue
            rc, rn = d["rise_off_um"], d["rise_on_um"]
            a = math.sqrt(rc*rc - rn*rn) if rc > rn else -math.sqrt(rn*rn - rc*rc)
            print(f"{r['name']:>5} {r['floor_um']:7.4f} {fam:>8} {rc:9.3f} {rn:9.3f} "
                  f"{rc-rn:8.3f} {a:9.3f} {d.get('shift_dy',0):3d},{d.get('shift_dx',0):<3d} "
                  f"{d['contrast_off']:8.0f} {d['contrast_on']:8.0f}")
            rows.append(dict(stack=stack, roi=r["name"], family=fam, admitted=True,
                             floor_um=r["floor_um"], rise_cr=rc, rise_nn=rn,
                             a_per_roi=a, shift=(d.get("shift_dy",0), d.get("shift_dx",0))))
    print()

print("=== the flip, measured DIRECTLY: ref=cr-plane, arm=cr-fullres ===")
print(f"{'ROI':>5} {'floor':>7} {'rise_plane':>11} {'rise_fullres':>13} {'delta_um':>9} "
      f"{'delta_%':>8} {'shift':>8}  verdict")
direct = []
for stack in ("109MSDCF", "tweezers", "ruler"):
    sub = STACK_DIR[stack]
    for r in [x for x in rois if x["stack"] == stack and x["admitted"]]:
        pp, _ = plane(sub, "cr-plane"); pf, _ = plane(sub, "cr-fullres")
        if pp is None or pf is None: continue
        d = M.paired_delta_registered(pp, pf, r["roi"], r["axis"])
        if d.get("error"):
            print(f"{r['name']:>5} {r['floor_um']:7.4f}   ERROR {d['error'][:70]}"); continue
        dm = d["rise_off_um"] - d["rise_on_um"]
        v = ("SHARPER" if dm > r["floor_um"] else
             "softer"  if dm < -r["floor_um"] else "null (below floor)")
        print(f"{r['name']:>5} {r['floor_um']:7.4f} {d['rise_off_um']:11.3f} "
              f"{d['rise_on_um']:13.3f} {dm:9.3f} "
              f"{100*dm/d['rise_off_um']:8.2f} {d.get('shift_dy',0):3d},{d.get('shift_dx',0):<3d}  {v}")
        direct.append(dict(stack=stack, roi=r["name"], floor=r["floor_um"],
                           rise_plane=d["rise_off_um"], rise_fullres=d["rise_on_um"], delta=dm))

print("\n=== BUILD-SHARP's POOLED recipe: a = sqrt(mean(rise_cr)^2 - mean(rise_nn)^2) ===")
print("    pooled over admitted ROIs that scored in BOTH families\n")
ok = {}
for fam, _, _ in FAMILIES:
    ok[fam] = {(r["stack"], r["roi"]) for r in rows if r["family"] == fam and "rise_cr" in r}
common = ok["plane"] & ok["fullres"]
print(f"    common admitted ROIs: {sorted(common)}\n")
print(f"{'family':>9} {'n':>3} {'mean rise_cr':>13} {'mean rise_nn':>13} {'a_pooled_um':>12}")
res = {}
for fam, _, _ in FAMILIES:
    sel = [r for r in rows if r["family"] == fam and (r["stack"], r["roi"]) in common]
    mc = float(np.mean([r["rise_cr"] for r in sel]))
    mn = float(np.mean([r["rise_nn"] for r in sel]))
    a = math.sqrt(mc*mc - mn*mn) if mc > mn else -math.sqrt(mn*mn - mc*mc)
    res[fam] = dict(n=len(sel), mc=mc, mn=mn, a=a)
    print(f"{fam:>9} {len(sel):3d} {mc:13.4f} {mn:13.4f} {a:12.4f}")

print(f"\n    BUILD-SHARP published (plane gather, its own pin): 14.9774 um")
print(f"    V-GATHER plane   family, same recipe            : {res['plane']['a']:.4f} um")
print(f"    V-GATHER fullres family, same recipe            : {res['fullres']['a']:.4f} um")

print("\n=== closure ===")
OPTICS, GATED = 30.44, 7.61
for fam in ("plane", "fullres"):
    a = res[fam]["a"]
    pred = math.sqrt(OPTICS**2 + a**2 + GATED**2)
    meas = float(np.mean([d["rise_plane"] if fam == "plane" else d["rise_fullres"]
                          for d in direct if (d["stack"], d["roi"]) in
                          {("109MSDCF", "M94"), ("tweezers", "TW1")}]))
    print(f"  {fam:>8}: predicted sqrt(30.44^2 + {a:.2f}^2 + 7.61^2) = {pred:7.3f} um   "
          f"measured(M94,TW1 @gate0) = {meas:7.3f} um   gap = {100*(meas-pred)/meas:+6.2f}%")

Path(ESF / "esfscore.json").write_text(json.dumps(
    dict(rows=rows, direct=direct, pooled=res), indent=1, default=str))
print(f"\nwrote {ESF / 'esfscore.json'}")
