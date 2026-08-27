"""AVERAGING EFFICIENCY: how much noise power does the 20-frame merge remove,
per arm?  If the merge removes LESS from the fullres arm, the pyramid's
band-power-weighted SOFT selection is concentrating weight on fewer frames --
that, and not the double demosaic, is what manufactures the excess.
Ideal unweighted mean of N frames removes a factor N.
"""
from __future__ import annotations
import sys, math, numpy as np
sys.path.insert(0, r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-GATHER")
from chroma_g0m import run, _ctr, NB, pred
N = 12   # gate0 renders used --limit 12; merge renders used --limit 20
print("Band power REMOVED by the merge, per arm  =  P(gate0) / P(merge).")
print("Higher = more effective averaging.  An unweighted mean of N frames gives N.")
print()
for s in ("foam", "couch-fibers-cpl"):
    m0,m1,lm0,lm1,_ = run(s,"q")
    g0,g1,lg0,lg1,_ = run(s,"gate0")
    print(f"=== {s} ===")
    print(f"{'f':>8} | {'CHROMA g0':>10} {'CHROMA g1':>10} {'g0/g1':>7} | "
          f"{'LUMA g0':>9} {'LUMA g1':>9} {'g0/g1':>7}")
    for i in range(0,NB,2):
        ac0,ac1 = g0[i]/m0[i], g1[i]/m1[i]
        al0,al1 = lg0[i]/lm0[i], lg1[i]/lm1[i]
        print(f"{_ctr[i]:8.4f} | {ac0:10.2f} {ac1:10.2f} {ac0/ac1:7.2f} | "
              f"{al0:9.2f} {al1:9.2f} {al0/al1:7.2f}")
    sub=[i for i in range(NB) if 2*_ctr[i]<0.5]
    c0=sum(g0[i] for i in sub)/sum(m0[i] for i in sub)
    c1=sum(g1[i] for i in sub)/sum(m1[i] for i in sub)
    l0=sum(lg0[i] for i in sub)/sum(lm0[i] for i in sub)
    l1=sum(lg1[i] for i in sub)/sum(lm1[i] for i in sub)
    print(f"  band-integrated f<0.25:  chroma  plane {c0:.2f}x  fullres {c1:.2f}x  "
          f"-> the merge removes {c0/c1:.2f}x MORE from the plane arm")
    print(f"                           luma    plane {l0:.2f}x  fullres {l1:.2f}x  "
          f"-> {l0/l1:.2f}x MORE from the plane arm")
    print()
