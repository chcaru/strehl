"""Emit the section 18 markdown table from c3_chroma.json."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

ORDER = ["off", "shipped (rust)", "shipped (python)", "self R only (python)",
         "self B only (python)", "self (python)"]

with open(os.path.join(common.OUT, "json", "c3_chroma.json")) as fh:
    res = json.load(fh)

print("| stack | arm | EDGE | dEDGE | FLAT | dFLAT | edge/flat |")
print("|---|---|---|---|---|---|---|")
for r in res:
    by = {a["arm"]: a for a in r["arms"]}
    att = [a for a in r["arms"] if a["arm"].startswith("self/atten")]
    names = ORDER + [a["arm"] for a in att]
    for i, k in enumerate(names):
        if k not in by:
            continue
        a = by[k]
        st = f"**{r['stack']}**" if i == 0 else ""
        rat = ("--" if a["arm"] == "off"
               else f"{a['edge_over_flat']:.0f}x")
        de = "--" if a["arm"] == "off" else f"{a['d_edge_pct']:+.2f}%"
        df = "--" if a["arm"] == "off" else f"{a['d_flat_pct']:+.2f}%"
        print(f"| {st} | {a['arm']} | {a['edge']:.6f} | {de} | "
              f"{a['flat']:.6f} | {df} | {rat} |")

print()
print("| stack | emulation recovery | shipped-py R | self-py R only | winner |")
print("|---|---|---|---|---|")
nwin = 0
for r in res:
    by = {a["arm"]: a for a in r["arms"]}
    s = by["shipped (python)"]["d_edge_pct"]
    v = by["self R only (python)"]["d_edge_pct"]
    w = "shipped" if s < v else "self"
    nwin += w == "shipped"
    print(f"| {r['stack']} | {r['emulation_recovery_pct']:.1f}% | {s:+.2f}% | "
          f"{v:+.2f}% | **{w}** |")
print(f"\nshipped red wins {nwin}/{len(res)}")

print()
print("| stack | blue alone dEDGE | blue alone dFLAT | blue adds on top of R |")
print("|---|---|---|---|")
for r in res:
    by = {a["arm"]: a for a in r["arms"]}
    b = by["self B only (python)"]
    add = (by["self (python)"]["d_edge_pct"]
           - by["self R only (python)"]["d_edge_pct"])
    print(f"| {r['stack']} | {b['d_edge_pct']:+.2f}% | "
          f"{b['d_flat_pct']:+.2f}% | {add:+.2f} pp |")
