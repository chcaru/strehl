"""Two questions answered from the registered ray profiles alone.

Q1  Does the ring survive ORCH's own bin edges? If rebinning MY profile with
    ORCH's edges makes the ring vanish, the coarse binning is the cause of the
    published negative and nothing else needs to be argued.

Q2  Where do the two subjects actually agree? C1's evidence is one number taken
    1-4 px from a step edge. Print the whole comparison and let the reader see
    at which distances the agreement exists.
"""
import json
from pathlib import Path
import numpy as np

J = Path(r"C:\dev\strehl-out\V-RIM\json2")
cb = json.loads((J / "coffee-bean-rays.json").read_text())
fb = json.loads((J / "flower-bud-rays.json").read_text())

ORCH_EDGES = [0, 4, 8, 12, 16, 20, 25, 30, 40, 50, 65, 80, 100, 125, 150,
              200, 250, 300]


def rebin(rec, edges):
    g = np.array(rec["grid"]); m = np.array(rec["med"])
    out = []
    for i in range(len(edges) - 1):
        s = (g >= edges[i]) & (g < edges[i + 1])
        if s.sum() == 0:
            continue
        out.append((0.5 * (edges[i] + edges[i + 1]), float(m[s].mean()),
                    edges[i], edges[i + 1]))
    return out


def orch_prom(binned, ref):
    v = np.array([b[1] for b in binned]); d = np.array([b[0] for b in binned])
    best = None
    for i in range(1, len(v) - 1):
        if v[i] >= v[i - 1] and v[i] > v[i + 1]:
            p = float(v[i] - v[i + 1:].min())
            if best is None or p > best[2]:
                best = (float(d[i]), float(v[i]), p)
    return best


print("Q1  MY coffee-bean ray profile, rebinned with ORCH's edges")
print("    (same pixels, same registration, only the bin edges change)")
for key, name in (("all", "all rays"), ("straight", "straightest quartile")):
    rec = cb[key]
    ref = rec["far"]
    fine = rebin(rec, list(range(0, 301)))
    coarse = rebin(rec, ORCH_EDGES)
    pf = orch_prom(fine, ref)
    pc = orch_prom(coarse, ref)
    print(f"  {name}:")
    print("     ORCH bin      mean DN     vs far     frac")
    for d, v, lo, hi in coarse:
        print(f"     {lo:4d}-{hi:<4d} {v:11.1f} {v-ref:+10.1f} "
              f"{(v-ref)/ref*100:+7.2f}%")
    print(f"     ring with 1 px bins    : d={pf[0]:.0f} px, {pf[2]:+.0f} DN "
          f"= {pf[2]/ref*100:+.2f}%")
    if pc:
        print(f"     ring with ORCH's bins  : d={pc[0]:.0f} px, {pc[2]:+.0f} DN "
              f"= {pc[2]/ref*100:+.2f}%")
    else:
        print("     ring with ORCH's bins  : NONE FOUND -- profile reads monotone")
    print()

print("Q2  where the two subjects agree, and where they do not")
print("    all-ray registered profiles, both normalisations")
print("      t     cb %far    fb %far   |diff|      cb %con    fb %con   |diff|")
gc = np.array(cb["all"]["grid"]); mc = np.array(cb["all"]["med"])
gf = np.array(fb["all"]["grid"]); mf = np.array(fb["all"]["med"])
cbf, cbi = cb["all"]["far"], cb["all"]["inner"]
fbf, fbi = fb["all"]["far"], fb["all"]["inner"]
for t in [0, 1, 2, 4, 8, 12, 16, 20, 30, 40, 50, 65, 80, 100, 125, 150,
          175, 200, 250, 300]:
    a = float(np.interp(t, gc, mc)); b = float(np.interp(t, gf, mf))
    af, bf_ = (a - cbf) / cbf * 100, (b - fbf) / fbf * 100
    ac, bc = (a - cbf) / (cbf - cbi) * 100, (b - fbf) / (fbf - fbi) * 100
    print(f"  {t:5d}  {af:+9.2f}% {bf_:+9.2f}% {abs(af-bf_):7.2f}   "
          f"{ac:+9.2f}% {bc:+9.2f}% {abs(ac-bc):7.2f}")

print()
print("Q3  ring prominence by local fringe density, within each subject")
for nm, d in (("coffee-bean", cb), ("flower-bud", fb)):
    for k in ("straight", "all", "fringed"):
        r = d.get(k)
        if r and r["ring"]:
            print(f"  {nm:12s} {k:9s} n={r['n']:5d}  ring t={r['ring']['t']:5.0f} px "
                  f"{r['ring']['frac']*100:+7.2f}%   edge {r['frac1']*100:+7.2f}% far "
                  f"{r['frac1_contrast']*100:+7.2f}% contrast")
