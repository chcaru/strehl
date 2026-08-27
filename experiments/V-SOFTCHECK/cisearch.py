"""Block-bootstrap CIs for the search-max arm, plus the null-normalised value.

The search-max denominator is a max over 25 offsets x N frames, so it has a
large order statistic of its own; the null (N+1 iid noised masters put
through the IDENTICAL construction, true ratio 1.000) measures it, and the
normalised column divides it out.
"""
import os, sys, numpy as np, softcheck as S
CN = 0.185088
H,W,T,STEP,MARGIN = 2344,3516,128,64,176
ny = len(np.arange(MARGIN,H-MARGIN-T+1,STEP)); nx = len(np.arange(MARGIN,W-MARGIN-T+1,STEP))
print(f"{'subject':22s} {'search-max NOSUB':>25s} {'null':>7s} {'norm':>7s} |"
      f" {'search-max SUB':>25s} {'null':>7s} {'norm':>7s}")
for subj in sys.argv[1:]:
    f = os.path.join(S.ROOT,"cache",f"{subj}--searchmax.npz")
    if not os.path.exists(f): print(f"{subj:22s}  (not finished)"); continue
    c = np.load(f)
    Mm,Mh,Mlo,bm,bh = c["Mm"],c["Mh"],c["Mlo"],c["bm"],c["bh"]
    nm,nh,n0m,n0h = c["nm"],c["nh"],c["n0m"],c["n0h"]
    sel = Mlo >= np.median(Mlo); ntot = len(Mlo)
    res=[]
    for num,den,nn,nd in ((Mm,bm,n0m,nm),(Mm-CN*Mh,bm-CN*bh,n0m-CN*n0h,nm-CN*nh)):
        ok = sel & (den>0) & np.isfinite(den) & np.isfinite(num)
        r = num[ok]/den[ok]
        ci = S.block_ci(r, ok, (ny,nx), ntot)
        okn = sel & (nd>0); nul = float(np.median(nn[okn]/nd[okn]))
        res.append((float(np.median(r)), ci, nul))
    a,b = res
    print(f"{subj:22s} {a[0]:7.4f} [{a[1][0]:.4f},{a[1][1]:.4f}] {a[2]:7.4f} {a[0]/a[2]:7.4f} |"
          f" {b[0]:7.4f} [{b[1][0]:.4f},{b[1][1]:.4f}] {b[2]:7.4f} {b[0]/b[2]:7.4f}")
