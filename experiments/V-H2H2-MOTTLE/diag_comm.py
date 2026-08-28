import numpy as np, sys, os
sys.path.insert(0, ".")
import bandlib, decomplib
y,x = np.mgrid[0:512,0:512].astype(float)
S = 40*np.sin(x/7)*np.cos(y/11) + 25*np.sin((x+y)/31) + 30*((x//37+y//41)%2) + 128
print("how much 20-60 band energy does each plant actually move?")
base = np.std(decomplib.bandpass(S,20,60))
for r in (1,3,8,15):
    b = np.std(decomplib.bandpass(bandlib.boxblur(S,r),20,60))
    print("  boxblur r=%-3d side %-3d -> band sd %8.4f  (x%.4f)" % (r,2*r+1,b,b/base))
print("  base band sd %.4f" % base)
print()
print("the 40x arm: why no degeneracy")
na = np.random.default_rng(1).normal(0,3,S.shape); nb = np.random.default_rng(2).normal(0,3,S.shape)
a, b40 = S+na, (S+nb)*40.0
for lbl,(p,q) in {"hs":( (a+b40)/2,None), "hd":((a-b40)/2,None)}.items():
    print("  %s band var %.6g" % (lbl, np.var(decomplib.bandpass(p,20,60))))
print("  -> both dominated by the 40x arm, ratio ~ (20.5/19.5)^2 = %.4f, guard never fires" % (20.5/19.5)**2)
print()
print("anticorrelated arms (a genuine construction that MUST fire):")
banti = 2*np.mean(a) - a
print("  hs band var %.6g   hd band var %.6g" % (
    np.var(decomplib.bandpass((a+banti)/2,20,60)), np.var(decomplib.bandpass((a-banti)/2,20,60))))
