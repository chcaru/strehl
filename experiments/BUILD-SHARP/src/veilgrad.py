import numpy as np, tifffile, sys
sys.path.insert(0, r"C:\dev\blog\death-of-software\projects\strehl\experiments\BUILD-SHARP\src")
from veilorlight import subject_mask
from scipy import ndimage
R = r"C:\dev\strehl-out\BUILD-SHARP\veil"
def load(s,a): return tifffile.imread(rf"{R}\{s}\{a}\linear-srgb.tif").astype(np.float32)
EDGES=[4,12,30,60,120,200,300,450,700,1200]
for s in ("flower-bud-alone-cpl","coffee-bean"):
    A=load(s,"A"); B=load(s,"B")
    m = subject_mask(A)
    d = ndimage.distance_transform_edt(~m)
    ga=A.mean(axis=2); gb=B.mean(axis=2)
    def grad(x):
        g=np.zeros_like(x); g[:-1,:]+=np.abs(np.diff(x,axis=0)); g[:,:-1]+=np.abs(np.diff(x,axis=1))
        return g
    Ga,Gb=grad(ga),grad(gb)
    print(f"\n=== {s}: gradient |grad| mean, ABSOLUTE DN, by distance from subject ===")
    print(f"{'d (px)':>12}{'A':>10}{'B':>10}{'delta':>10}{'delta %':>10}")
    for lo,hi in zip(EDGES[:-1],EDGES[1:]):
        sel=(d>=lo)&(d<hi)
        if sel.sum()<1000: continue
        a,b=Ga[sel].mean(),Gb[sel].mean()
        print(f"{f'{lo}-{hi}':>12}{a:10.1f}{b:10.1f}{b-a:10.1f}{100*(b-a)/a:9.2f}%")
    sel=d>=1200
    if sel.sum()>1000:
        a,b=Ga[sel].mean(),Gb[sel].mean()
        print(f"{'>=1200':>12}{a:10.1f}{b:10.1f}{b-a:10.1f}{100*(b-a)/a:9.2f}%")
    sel=m
    a,b=Ga[sel].mean(),Gb[sel].mean()
    print(f"{'SUBJECT':>12}{a:10.1f}{b:10.1f}{b-a:10.1f}{100*(b-a)/a:9.2f}%")
    del A,B,Ga,Gb
