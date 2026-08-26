"""Final n=26 summary.

Two rules are applied BEFORE any ring number is read, and both are stated here
rather than chosen per subject:

R1 POLARITY. C1 and C2 are claims about the BACKDROP outward from a subject
   that is darker than its backdrop. A subject whose interior is brighter than
   its backdrop is the opposite geometry: the outward profile falls instead of
   rising, so the dip statistic would score the edge transition itself. Those
   subjects are reported separately and excluded from the C1 and C2 tallies.

R2 EVERY SUBJECT LANDS IN A COUNTED OUTCOME. A subject whose rays fail to
   register is NOT MEASURED, which is not the same as no ring. A subject whose
   own null window exceeds a third of its ring is UNMEASURABLE BACKDROP. The
   printed counts sum to the number of pre-registered MEASURABLE subjects, so a
   skipped subject cannot be read as a clean negative.
"""
import json, re
from pathlib import Path
import numpy as np
import sys
sys.path.insert(0, r"C:\dev\strehl-out\V-RIM")
from ringstat import ring_and_null, RING_LO, RING_HI, NULL_LO, NULL_HI

JS = Path(r"C:\dev\strehl-out\V-RIM\json2")
PRE = Path(r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-RIM\preregistration.md")

cls = {}
for line in PRE.read_text(encoding="utf-8").splitlines():
    m = re.match(r"^\|\s*`?([A-Za-z0-9\-]+)`?\s*\|\s*(MEASURABLE|EXCLUDED)\s*\|\s*([A-Z\-]+)\s*\|", line)
    if m:
        cls[m.group(1)] = (m.group(2), m.group(3))
meas = [k for k, v in cls.items() if v[0] == "MEASURABLE"]
print(f"pre-registered: {len(cls)} subjects, {len(meas)} MEASURABLE "
      f"({sum(1 for k in meas if cls[k][1]=='FRINGED')} FRINGED, "
      f"{sum(1 for k in meas if cls[k][1]=='SMOOTH')} SMOOTH)")
print(f"ring window t=[{RING_LO:.0f},{RING_HI:.0f}] px; "
      f"null window t=[{NULL_LO:.0f},{NULL_HI:.0f}] px; "
      f"detection needs ring >= 3x that subject's own null\n")

recs = {}
for lab in meas:
    f = JS / f"{lab}-rays.json"
    if not f.exists():
        recs[lab] = dict(state="NOT RENDERED"); continue
    d = json.loads(f.read_text())
    if not d.get("all") or not d.get("straight"):
        recs[lab] = dict(state="NOT MEASURED (rays did not register)"); continue
    a, s, g = d["all"], d["straight"], d.get("fringed")
    pol = "dark-on-bright" if a["inner"] < a["far"] else "BRIGHT-on-dark"
    rs, ns = ring_and_null(s["grid"], s["med"], s["far"])
    rg, ng = ring_and_null(g["grid"], g["med"], g["far"]) if g else (None, None)
    det = rs["frac"] >= 3 * max(ns["frac"], 0.0005)
    recs[lab] = dict(state="OK", pol=pol, far=a["far"], inner=a["inner"],
                     frac1=a["frac1"], fc=a["frac1_contrast"],
                     pinned=-0.5 * (1 - a["inner"] / a["far"]),
                     rs=rs, ns=ns, rg=rg, ng=ng, det=det,
                     unmeas=(ns["frac"] > rs["frac"] / 3))

print("=== per subject, pre-registered class frozen before measurement ===")
print(f"{'subject':36s} {'class':8s} {'polarity':14s} {'edge %far':>9s} "
      f"{'straight ring':>14s} {'null':>7s} {'fringed ring':>13s} {'outcome':>12s}")
for lab in sorted(meas, key=lambda k: (cls[k][1], k)):
    r = recs[lab]
    if r["state"] != "OK":
        print(f"{lab:36s} {cls[lab][1]:8s} {'-':14s} {'-':>9s} {'-':>14s} "
              f"{'-':>7s} {'-':>13s} {r['state']:>12s}")
        continue
    out = ("RING" if r["det"] else ("unmeasurable" if r["unmeas"] else "no ring"))
    if r["pol"] != "dark-on-bright":
        out = "polarity"
    print(f"{lab:36s} {cls[lab][1]:8s} {r['pol']:14s} {r['frac1']*100:+9.2f} "
          f"{r['rs']['frac']*100:+9.2f}@{r['rs']['t_peak']:3.0f} {r['ns']['frac']*100:6.2f}% "
          f"{r['rg']['frac']*100:+8.2f}@{r['rg']['t_peak']:3.0f} {out:>12s}")

ok = [l for l in meas if recs[l]["state"] == "OK" and recs[l]["pol"] == "dark-on-bright"]
print(f"\noutcome partition over {len(meas)} MEASURABLE subjects:")
cats = {}
for l in meas:
    r = recs[l]
    if r["state"] != "OK":
        k = r["state"]
    elif r["pol"] != "dark-on-bright":
        k = "excluded by R1 polarity"
    elif r["det"]:
        k = "RING detected"
    elif r["unmeas"]:
        k = "backdrop too noisy to decide"
    else:
        k = "no ring"
    cats[k] = cats.get(k, 0) + 1
for k, v in sorted(cats.items()):
    print(f"    {k:36s} {v:3d}")
print(f"    {'TOTAL':36s} {sum(cats.values()):3d}")

print(f"\n=== C2 across subjects, like-polarity only (n={len(ok)}) ===")
for c in ("SMOOTH", "FRINGED"):
    v = [(l, recs[l]["rs"]["frac"] * 100) for l in ok if cls[l][1] == c]
    if not v:
        continue
    arr = np.array([x[1] for x in v])
    print(f"  {c:8s} n={len(v)}  mean {arr.mean():+6.2f}%  max {arr.max():+6.2f}%  "
          f"({max(v, key=lambda x: x[1])[0]})")
sm = [(l, recs[l]["rs"]["frac"] * 100) for l in ok if cls[l][1] == "SMOOTH"]
fr = [(l, recs[l]["rs"]["frac"] * 100) for l in ok if cls[l][1] == "FRINGED"]
if sm and fr:
    top = max(sm, key=lambda x: x[1])
    print(f"  C2 predicts SMOOTH near zero. Strongest SMOOTH is {top[0]} at "
          f"{top[1]:+.2f}%, which exceeds {sum(1 for _, x in fr if x < top[1])} "
          f"of {len(fr)} FRINGED subjects.")

print(f"\n=== C2 within subject: fringed quartile vs straight quartile (n={len(ok)}) ===")
w = [(l, recs[l]["rg"]["frac"] * 100, recs[l]["rs"]["frac"] * 100) for l in ok]
bigger = sum(1 for _, g, s in w if g > s)
print(f"  the most-fringed quartile shows the larger ring in {bigger} of {len(w)} subjects")
for l, g, s in sorted(w, key=lambda x: -(x[1] - x[2])):
    print(f"    {l:36s} fringed {g:+6.2f}%   straight {s:+6.2f}%   "
          f"ratio {(g/s if s > 0.01 else float('nan')):5.1f}x")

print(f"\n=== C1 across subjects, like-polarity only (n={len(ok)}) ===")
print(f"{'subject':36s} {'class':8s} {'%far':>8s} {'pinned':>8s} {'%contrast':>10s}")
for l in sorted(ok):
    r = recs[l]
    print(f"{l:36s} {cls[l][1]:8s} {r['frac1']*100:+8.2f} {r['pinned']*100:+8.2f} "
          f"{r['fc']*100:+10.2f}")
a = np.array([recs[l]["frac1"] * 100 for l in ok])
b = np.array([recs[l]["fc"] * 100 for l in ok])
print(f"\n  %far      min {a.min():+.2f}  max {a.max():+.2f}  SPREAD {np.ptp(a):.2f} points")
print(f"  %contrast min {b.min():+.2f}  max {b.max():+.2f}  SPREAD {np.ptp(b):.2f} points")
print(f"  ORCH treats a 1.7 point agreement between two members of this "
      f"population as evidence of optics.")
