import numpy as np, tifffile
files = [("flowerbud M1 (the 14.6 ladder input)","C:/dev/strehl-out/BUILD-HIGHLIGHT/flowerbud/M1-caon-kneeoff.tif"),
         ("ladder K3 stack demosaiced       ","C:/dev/strehl-out/BUILD-HIGHLIGHT/ladder/K3-stack-demo.tif"),
         ("ladder K5 stack ca-off           ","C:/dev/strehl-out/BUILD-HIGHLIGHT/ladder/K5-stack-caoff.tif"),
         ("ladder K2 stack binned CFA       ","C:/dev/strehl-out/BUILD-HIGHLIGHT/ladder/K2-stack-binned.tif")]
print("  %-34s %-8s %8s %7s %7s" % ("file","dtype","distinct","min","max"))
for nm,p in files:
    a = tifffile.imread(p)
    u = len(np.unique(a))
    print("  %-34s %-8s %8d %7d %7d   %s" % (nm, a.dtype, u, a.min(), a.max(),
          "OK 16-bit" if u > 2000 else "*** SUSPECT ***"))
    del a
