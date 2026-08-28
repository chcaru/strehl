import numpy as np, sys, os, tifffile
sys.path.insert(0,"."); import bandlib, decomplib
OLD=r"C:\dev\strehl-out\V-H2H2\ladder\out"; expo=2.6898; S=384
def g(n): return bandlib.display(tifffile.imread(os.path.join(OLD,n))[...,1].astype(np.float64), expo)
a,b = g("n149a.tiff"), g("n149b.tiff")
print("GLOBAL (whole frame): is the level difference real or an artifact of the shifted window?")
print("  arm a mean %.4f  sd %.4f  iqr %.4f" % (a.mean(), a.std(), np.subtract(*np.percentile(a,[75,25]))))
print("  arm b mean %.4f  sd %.4f  iqr %.4f" % (b.mean(), b.std(), np.subtract(*np.percentile(b,[75,25]))))
print("  mean ratio %.5f   iqr ratio %.5f" % (a.mean()/b.mean(), np.subtract(*np.percentile(a,[75,25]))/np.subtract(*np.percentile(b,[75,25]))))
print()
print("PER-SITE, unshifted vs shifted, at the detail site used above (offset -3,+17):")
for (y,x) in [(2520,984),(3288,600),(984,5208)]:
    ca=a[y:y+S,x:x+S]; cu=b[y:y+S,x:x+S]; cr=b[y-3:y-3+S,x+17:x+17+S]
    print("  site (%4d,%4d): a %.3f | b unshifted %.3f (%+.2f%%) | b shifted %.3f (%+.2f%%)"
          % (y,x,ca.mean(),cu.mean(),100*(cu.mean()/ca.mean()-1),cr.mean(),100*(cr.mean()/ca.mean()-1)))
print()
print("does a pure LEVEL offset survive the band filter? (it must not)")
t = a[2520:2520+S,984:984+S]
print("  band sd of t      %.6f" % np.std(decomplib.bandpass(t,20,60)))
print("  band sd of t+10   %.6f  (offset removed by the filter)" % np.std(decomplib.bandpass(t+10.0,20,60)))
print("  band sd of t*1.04 %.6f  (gain is NOT removed: x%.4f)" % (np.std(decomplib.bandpass(t*1.04,20,60)), np.std(decomplib.bandpass(t*1.04,20,60))/np.std(decomplib.bandpass(t,20,60))))
