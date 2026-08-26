import numpy as np, tifffile
R = r"C:\dev\strehl-out\BUILD-SHARP\veil"
def load(s,a): return tifffile.imread(rf"{R}\{s}\{a}\linear-srgb.tif")
print(f"{'subject':<22}{'arm':>4}{'px at 65535':>14}{'% of frame':>12}{'>=65000':>12}")
for s in ("flower-bud-alone-cpl","109MSDCF","coffee-bean","couch-fibers-cpl"):
    for a in ("A","B"):
        x = load(s,a)
        n = int((x >= 65535).any(axis=2).sum()); tot = x.shape[0]*x.shape[1]
        n2 = int((x >= 65000).any(axis=2).sum())
        print(f"{s:<22}{a:>4}{n:14,d}{100*n/tot:11.4f}%{100*n2/tot:11.4f}%")
        del x
