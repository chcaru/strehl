"""Cross-check: is V-NEVERWORSE's 0.30-0.35 cyc/px measurement band QUALIFIED
on the subjects it was measured on, and which DEEP subject is qualified there?

Reads only committed JSON from this lane. Produces no new measurement.
"""
import glob
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import bandsweep                                                 # noqa: E402

SKIP = ("simdecim", "bandsweep-far20-leaf-2-cpl")
BAND = "0.30-0.40"   # the FINE slice containing 0.30-0.35

recs = {}
for p in sorted(glob.glob(os.path.join(_HERE, "bandsweep-far20*.json"))):
    if any(s in os.path.basename(p) for s in SKIP):
        continue
    for r in json.load(open(p)):
        recs.setdefault(r["key"], r)

hdr = "{:<30}{:>6}{:>12}{:>16}{:>10}".format(
    "subject", "N", BAND + " R", "verdict", "boundary")
print(hdr)
print("-" * len(hdr))
for k, r in sorted(recs.items(), key=lambda kv: -kv[1]["n_real"]):
    v = r["bands"][BAND]
    print("{:<30}{:>6}{:>12.3f}{:>16}{:>10.2f}".format(
        k, r["n_real"], v["R"], v["verdict"], bandsweep.boundary(r)))

qual = [(k, r) for k, r in recs.items()
        if r["bands"][BAND]["verdict"] == "PASS"]
deep = sorted(qual, key=lambda kv: -kv[1]["n_real"])
print("\nQUALIFIED at {} (PASS), deepest first:".format(BAND))
for k, r in deep:
    print("  {:<30} N={:<5} R={:.3f}".format(k, r["n_real"], r["bands"][BAND]["R"]))
print("\nNOT qualified at {}:".format(BAND))
for k, r in sorted(recs.items()):
    if r["bands"][BAND]["verdict"] != "PASS":
        print("  {:<30} N={:<5} R={:.3f}  {}".format(
            k, r["n_real"], r["bands"][BAND]["R"], r["bands"][BAND]["verdict"]))
