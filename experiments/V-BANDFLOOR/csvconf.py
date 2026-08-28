import csv, numpy as np
rows=list(csv.DictReader(open(r"D:\strehl-out\ORCH-EYE\avgband.csv")))
n=np.array([float(r["N"]) for r in rows]); b0=np.array([float(r["b0"]) for r in rows])
name=[r["subject"] for r in rows]
print("subjects=%d  b0 range %.1f-%.1f mean %.1f" % (len(rows), b0.min(), b0.max(), b0.mean()))
def spear(a,b):
    ra=np.argsort(np.argsort(a)); rb=np.argsort(np.argsort(b))
    return float(np.corrcoef(ra,rb)[0,1])
print("Spearman b0 vs N = %+.3f   Pearson = %+.3f" % (spear(n,b0), float(np.corrcoef(n,b0)[0,1])))
# ORCH's labelled groups
soft=["flowers-cpl","leaf-2-cpl","lead-1-cpl","flower-bud-alone-cpl"]
good=["flat-on-ruler-cpl","highly-angled-ruler-mm","wrapped-text-1","foam","coffee-bean","bee-3-cpl","bee-1-cpl","wrapped-text-2"]
d={r["subject"]:(float(r["N"]),float(r["b0"])) for r in rows}
for lbl,grp in (("SOFT",soft),("GOOD",good)):
    v=[d[s] for s in grp if s in d]
    if v:
        Ns=[x[0] for x in v]; Bs=[x[1] for x in v]
        print("%-5s n=%d  N median %.0f (range %.0f-%.0f)   b0 median %.1f"
              % (lbl,len(v),np.median(Ns),min(Ns),max(Ns),np.median(Bs)))
print()
print("%-28s %5s %6s" % ("subject","N","b0"))
for s,(N,B) in sorted(d.items(), key=lambda kv:-kv[1][1]):
    m = "SOFT" if s in soft else ("GOOD" if s in good else "")
    print("%-28s %5.0f %6.1f  %s" % (s,N,B,m))
