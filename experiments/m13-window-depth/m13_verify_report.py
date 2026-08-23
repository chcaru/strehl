"""Verify the exact numbers quoted in docs/research/M13-window-depth-measured.md.

Every headline figure in the report is recomputed here from the committed CSVs
and printed with its rule, so a reader can check the report against the data
without re-running the sweep.
"""

import csv
import os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")


def rows(name):
    with open(os.path.join(DATA, name), newline="") as f:
        return list(csv.DictReader(f))


print("== adaptive: range of oracle and realisable gains ==")
rr = rows("adaptive-109MSDCF.csv")
groups = defaultdict(list)
for r in rr:
    groups[(r["narrow"], r["wide"], int(r["step"]))].append(r)
for lbl, keep in (("all configurations", lambda s: True),
                  ("step > 0 only", lambda s: s > 0),
                  ("step == 0 (null)", lambda s: s == 0)):
    og, rg, n5, nneg = [], [], 0, 0
    for k, g in groups.items():
        if not keep(k[2]):
            continue
        nar = next(float(r["rms_band"]) for r in g if r["arm"] == f"fixed:{k[0]}")
        wid = next(float(r["rms_band"]) for r in g if r["arm"] == f"fixed:{k[1]}")
        orc = next(float(r["rms_band"]) for r in g if r["arm"] == "oracle:min-error")
        best = min(float(r["rms_band"]) for r in g if r["arm"] == "rule:disagree")
        base = min(nar, wid)
        o = 100.0 * (base - orc) / base
        q = 100.0 * (base - best) / base
        og.append(o)
        rg.append(q)
        n5 += o >= 5.0
        nneg += q < 0
    print(f"  {lbl}: n = {len(og)}")
    print(f"    oracle gain    : min {min(og):.2f}%  max {max(og):.2f}%   "
          f">=5%: {n5}/{len(og)}")
    print(f"    realisable gain: min {min(rg):.2f}%  max {max(rg):.2f}%   "
          f"negative: {nneg}/{len(rg)}")

print()
print("== 109MSDCF / vertical / step 32: acc, E_excess, bleed_fg ==")
rr = [r for r in rows("edge-109MSDCF.csv")
      if int(r["width"]) == 1 and int(r["step"]) == 32 and r["shape"].startswith("vertical")]
by = defaultdict(list)
for r in rr:
    by[int(r["window"])].append(r)
print(f"  {'w':>4} {'acc':>8} {'E_excess':>9} {'bleed_fg':>9}")
for w in sorted(by):
    g = by[w]
    a = sum(float(r["acc"]) for r in g) / len(g)
    e = sum(float(r["excess_dn"]) for r in g) / len(g)
    b = sum(float(r["bleed_fg"]) for r in g) / len(g)
    print(f"  {w:>4} {a:>8.4f} {e:>9.2f} {b:>9.2f}")
e15 = sum(float(r["excess_dn"]) for r in by[15]) / len(by[15])
e40 = sum(float(r["excess_dn"]) for r in by[40]) / len(by[40])
print(f"  w40 vs w15 optimum: {100*(e40-e15)/e15:.1f}% worse "
      f"(rule: 100*(E40-E15)/E15)")

print()
print("== N reduction in excess, w5 -> w13 ==")
per = defaultdict(list)
for stk in ("109MSDCF", "119MSDCF"):
    b = defaultdict(list)
    for r in rows(f"noise-{stk}.csv"):
        if r["roi_kind"] != "flat" or int(r["width"]) != 1:
            continue
        b[int(r["window"])].append(float(r["ratio"]))
    for w, v in b.items():
        v = sorted(v)
        per[w].append(v[len(v) // 2] if len(v) % 2 else 0.5 * (v[len(v)//2-1] + v[len(v)//2]))
n = {w: sum(v) / len(v) for w, v in per.items()}
print(f"  N(w5)  = {n[5]:.4f}   excess {n[5]-1:.4f}")
print(f"  N(w8)  = {n[8]:.4f}   excess {n[8]-1:.4f}")
print(f"  N(w13) = {n[13]:.4f}   excess {n[13]-1:.4f}")
print(f"  reduction in excess w5->w13: {100*((n[5]-1)-(n[13]-1))/(n[5]-1):.1f}% "
      f"(rule: (excess5 - excess13)/excess5)")

print()
print("== cost: full table ==")
cr = rows("cost-109MSDCF.csv")
c = {r["measure"]: float(r["ms_per_frame_per_mpx"]) for r in cr}
for r in cr:
    print(f"  {r['measure']:>18} {float(r['ms_per_frame_per_mpx']):>8.4f}")
wv = [float(r["ms_per_frame_per_mpx"]) for r in cr
      if r["measure"].startswith("tenengrad-w") and int(r["window"]) > 0]
print(f"  windowed spread: min {min(wv):.4f} max {max(wv):.4f} "
      f"= {100*(max(wv)-min(wv))/min(wv):.2f}%")
print(f"  w5 {c['tenengrad-w5']:.4f}  w13 {c['tenengrad-w13']:.4f}  "
      f"delta {100*(c['tenengrad-w13']-c['tenengrad-w5'])/c['tenengrad-w5']:+.2f}%")
print(f"  ring-1-3 {c['ring-1-3']:.4f}  tenengrad-w5 is "
      f"{100*(c['tenengrad-w5']-c['ring-1-3'])/c['ring-1-3']:+.2f}% of it")

print()
print("== support radius and tap count at w13 ==")
r13 = next(r for r in rows("cost-109MSDCF.csv") if r["measure"] == "tenengrad-w13")
sr = int(r13["support_radius"])
print(f"  support_radius from the harness: {sr}")
print(f"  analytic (2*sr+1)^2 = {(2*sr+1)**2} taps")

print()
print("== phi at the windows the report quotes (delta = 8 DN) ==")
for f in ("phi-109MSDCF.csv", "phi-109MSDCF-nonorm.csv"):
    print(f"  {f}")
    for r in rows(f):
        if float(r["delta"]) == 8.0 and int(r["window"]) in (0, 13, 15, 17, 40):
            print(f"    w{r['window']:>3}  phi {float(r['phi']):.9f}  taps {r['taps']}")
