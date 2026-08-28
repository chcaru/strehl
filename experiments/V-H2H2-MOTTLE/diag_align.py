import numpy as np, sys, os, tifffile
sys.path.insert(0,"."); import bandlib, decomplib
OUT=r"C:\dev\strehl-out\V-H2H2\ladder\out"
SITE=384; expo=2.6898
det=(2520,984); flat=(3288,1368)
def g(p,y,x,pad=24):
    a=tifffile.imread(p)[y-pad:y+SITE+pad, x-pad:x+SITE+pad, 1].astype(np.float64)
    return bandlib.display(a,expo)
print("within-rung a-vs-b integer offset, measured on the top detail site")
print("(both arms render the SAME scene; if they land on different grids the")
print(" half-difference contains scene edges and the decomposition is void)")
for n in (18,37,74,149):
    A=g(os.path.join(OUT,"n%da.tiff"%n),*det); B=g(os.path.join(OUT,"n%db.tiff"%n),*det)
    best=None
    for dy in range(-12,13):
        for dx in range(-12,13):
            e=float(np.mean(np.abs(A[24:24+SITE,24:24+SITE]-B[24+dy:24+dy+SITE,24+dx:24+dx+SITE])))
            if best is None or e<best[0]: best=(e,dy,dx)
    e0=float(np.mean(np.abs(A[24:24+SITE,24:24+SITE]-B[24:24+SITE,24:24+SITE])))
    print("  n%-4d best offset (%+d,%+d) mean|diff| %7.3f   at (0,0) %7.3f   improvement %5.2fx"
          %(n,best[1],best[2],best[0],e0,e0/best[0]))
