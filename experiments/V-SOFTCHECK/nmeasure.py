"""Measure the depth curve from masters rendered by nrender.py.

Uses the SAME statistic commissioned in ncurve.py (imported, not re-typed), so
the four-arm commissioning covers this code path.  Every arm is divided by the
DEEPEST arm, i.e. the configuration that actually ships.  A value ABOVE 1 means a
SHALLOWER stack produced a SHARPER master than the full stack -- the depth cost.
"""
import os, sys, numpy as np, softcheck as S
from ncurve import rings, pick_tiles, align_int, boot, EDGES, T, NT
ROOT=r"C:\dev\strehl-out\V-SOFTCHECK\ncurve"
subj=sys.argv[1]
d=os.path.join(ROOT,subj)
fs=sorted(f for f in os.listdir(d) if f.startswith("master-N") and f.endswith(".tiff"))
ns=[int(f[8:11]) for f in fs]
deep=fs[int(np.argmax(ns))]; Nmax=max(ns)
B=S.load_luma(os.path.join(d,deep),"srgb")
oy,ox=pick_tiles(B)
base=rings(B,oy,ox)
print(f"{subj}: depth curve, pin 9b05d0b7 / 44C2F2CD2E5B2894, merge backend pyramid")
print(f"  baseline = deepest arm N={Nmax} ({deep}); {NT} tiles T={T}; shipping grid {B.shape}")
print(f"  values >1 mean the SHALLOWER stack is SHARPER than the full stack\n")
hdr="  ".join(f"{a:.2f}-{b:.2f}" for a,b in zip(EDGES[:-1],EDGES[1:]))
print(f"  {'N':>4s}  {'shift':>9s}  {hdr}")
rows={}
for f,n in zip(fs,ns):
    M=S.load_luma(os.path.join(d,f),"srgb")
    sy,sx=align_int(B,M)
    r=rings(M,oy+sy,ox+sx)/np.maximum(base,1e-30)
    med=np.median(r,axis=0); rows[n]=(med,r)
    cells="  ".join(f"{v:9.4f}" for v in med)
    print(f"  {n:4d}  {sy:+4d},{sx:+4d}  {cells}")
    del M
print()
for b in range(len(EDGES)-1):
    peak=max(rows, key=lambda n: rows[n][0][b])
    lo,hi=boot(rows[peak][1][:,b])
    cost=(rows[peak][0][b]-1.0)*100
    tag="SIG" if lo>1.0 else "ns "
    print(f"  band {EDGES[b]:.2f}-{EDGES[b+1]:.2f}: sharpest at N={peak:3d}, "
          f"{cost:+6.1f}% vs N={Nmax}  CI [{lo:.4f},{hi:.4f}] {tag}")
np.savez(os.path.join(ROOT,f"{subj}--curve.npz"),
         ns=np.array(ns), med=np.array([rows[n][0] for n in ns]), EDGES=EDGES)
