import json, glob, os
# The gate-floor knob operates on PYRAMID band 0 = the finest Laplacian level =
# the top octave of the sampling grid ~= 0.25-0.50 cyc/px.  That is the same
# range ORCH's corrected contrast_ms.py calls band 0.  The FINE partition slices
# it as 0.25-0.30, 0.30-0.40, 0.40-0.48.
B0 = ("0.25-0.30", "0.30-0.40", "0.40-0.48")
B1 = ("0.17-0.20", "0.20-0.25")
recs = {}
for f in glob.glob("bandsweep-far20*.json"):
    if "simdecim" in f: continue
    for r in json.load(open(f)):
        recs.setdefault(r["key"], r)
order = ["112MSDCF","113MSDCF","119MSDCF","flower-bud-alone-cpl","leaf-2-cpl",
         "bee-1-cpl","flat-on-ruler-cpl","tweezers-cpl","lavendar-cpl",
         "dry-erase-marker-head-cpl","paper-sweep"]
print("PYRAMID BAND 0 (0.25-0.50 cyc/px) -- the band the gate-floor knob acts on")
print("rule: PASS = R>=2.0 and CI low>=1.5 | MARGINAL = 1.3<=R<2.0 | FAIL = R<1.3\n")
print(f"  {'subject':<28}{'0.25-0.30':>18}{'0.30-0.40':>18}{'0.40-0.48':>18}   band-0 verdict")
for k in order:
    r = recs.get(k)
    if not r:
        print(f"  {k:<28}{'-- not measured --':>54}")
        continue
    cells, vs = [], []
    for b in B0:
        v = r["bands"].get(b)
        if not v: cells.append("   n/a"); continue
        tag = {"PASS":"P","MARGINAL":"M"}.get(v["verdict"], "F")
        cells.append(f"{v['R']:12.3f} {tag}")
        vs.append(v["verdict"])
    ok = all(v == "PASS" for v in vs)
    verdict = "SIGNAL" if ok else ("NOISE" if all(v.startswith("FAIL") for v in vs) else "MIXED")
    print(f"  {k:<28}" + "".join(f"{c:>18}" for c in cells) + f"   {verdict}")
